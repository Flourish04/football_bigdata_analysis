# 🎨 NiFi Processor Design - Chi Tiết Thiết Kế Flow

## 📋 Mục Lục

1. [Tổng Quan Kiến Trúc](#tổng-quan-kiến-trúc)
2. [Chi Tiết Từng Processor](#chi-tiết-từng-processor)
3. [Cấu Hình Controller Services](#cấu-hình-controller-services)
4. [Kết Nối Giữa Các Processor](#kết-nối-giữa-các-processor)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## 🏗️ Tổng Quan Kiến Trúc

### **Flow Diagram Hoàn Chỉnh:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      NIFI DATA FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │GenerateFlow  │──1──▶│ InvokeHTTP   │──2──▶│EvaluateJson  │  │
│  │File (Timer)  │      │  (API Call)  │      │Path (Parse)  │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│                                                       │          │
│                                                       │3         │
│                                                       ▼          │
│                              ┌──────────────────────────┐       │
│                              │   SplitJson (Matches)    │       │
│                              └──────────────────────────┘       │
│                                         │                        │
│                                         │4                       │
│                                         ▼                        │
│                              ┌──────────────────────────┐       │
│                              │  RouteOnAttribute        │       │
│                              │  (Filter Live Matches)   │       │
│                              └──────────────────────────┘       │
│                                    │              │              │
│                           Live     │5             │5a Finished   │
│                                    ▼              ▼              │
│                         ┌──────────────┐  ┌──────────────┐     │
│                         │UpdateAttribute│  │  LogAttribute │     │
│                         │ (Enrich Data) │  │  (Discard)    │     │
│                         └──────────────┘  └──────────────┘     │
│                                    │6                            │
│                                    ▼                             │
│                         ┌──────────────────────┐                │
│                         │   JoltTransformJSON   │                │
│                         │   (Transform Schema)  │                │
│                         └──────────────────────┘                │
│                                    │7                            │
│                                    ▼                             │
│                         ┌──────────────────────┐                │
│                         │   PublishKafkaRecord  │                │
│                         │  (Confluent Cloud)    │                │
│                         └──────────────────────┘                │
│                              │            │                       │
│                    Success   │8           │8a Failure            │
│                              ▼            ▼                       │
│                    ┌──────────────┐  ┌──────────────┐          │
│                    │ LogAttribute │  │ LogAttribute │          │
│                    │  (Success)   │  │   (Retry)    │          │
│                    └──────────────┘  └──────────────┘          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### **Luồng Dữ Liệu (SIMPLIFIED):**
1. **GenerateFlowFile** → Trigger mỗi 30 giây
2. **InvokeHTTP** → Gọi API `/matches` (không cần date params - API tự filter!)
3. **EvaluateJsonPath** → Parse JSON response
4. **SplitJson** → Tách từng match thành FlowFile riêng
5. **UpdateAttribute** → Thêm metadata (timestamp, source, match_type)
6. **JoltTransformJSON** → Transform schema để phù hợp Kafka
7. **PublishKafkaRecord** → Gửi tới Confluent Cloud
8. **Spark Streaming** → Tự động upsert tất cả messages vào PostgreSQL

### **⚡ API Behavior (Mặc định):**
- 🔄 **API tự động filter:** `dateFrom=today, dateTo=tomorrow`
- 📦 **Response bao gồm:** TIMED, IN_PLAY, PAUSED, FINISHED, POSTPONED, CANCELLED, SUSPENDED
- ✅ **Không cần query params!** Không lọc status!

### **Data Strategy (UPSERT-based):**
- 📨 **NiFi**: Gửi TẤT CẢ messages vào Kafka (không lọc status)
- 🔄 **Spark Streaming**: Tự động check và upsert mọi message
- ✅ **Benefits**: 
  - Đơn giản: Không cần logic lọc phức tạp ở NiFi
  - Linh hoạt: Spark xử lý mọi status (TIMED, IN_PLAY, PAUSED, FINISHED, etc.)
  - Idempotent: Upsert đảm bảo không duplicate data
  - Complete: Capture toàn bộ lifecycle của match (scheduled → live → finished)

### **Use Cases Supported:**
1. **Real-time Dashboard** → Hiển thị live scores đang diễn ra
2. **Match History** → Xem lại các trận đã kết thúc trong ngày
3. **Results Summary** → Tổng hợp kết quả tất cả matches hôm nay
4. **Analytics** → Phân tích performance trong ngày (live + finished)

---

## 🔨 Chi Tiết Từng Processor

### **1️⃣ GenerateFlowFile - Timer/Trigger**

**Mục đích:** Tạo trigger định kỳ để poll API

#### **Cấu hình:**

| Property | Value | Giải thích |
|----------|-------|-----------|
| **Scheduling Strategy** | Timer driven | Chạy theo thời gian |
| **Run Schedule** | `30 sec` | Polling mỗi 30 giây |
| **Execution** | Primary Node | Chỉ chạy trên 1 node (nếu cluster) |
| **Custom Text** | `trigger` | Nội dung FlowFile (không quan trọng) |

#### **Properties Tab:**
```properties
Scheduling:
  Scheduling Strategy: Timer driven
  Run Schedule: 30 sec
  Concurrent Tasks: 1
  
Settings:
  Automatically Terminate Relationships: (none)
  Penalty Duration: 30 sec
  Yield Duration: 1 sec
  Bulletin Level: WARN
```

#### **Lưu ý:**
- ⚠️ **Rate Limit**: Football-Data.org FREE tier = 10 requests/min
- ✅ 30 giây = 2 requests/min → An toàn
- 💡 Có thể điều chỉnh dựa trên API plan của bạn

---

### **2️⃣ InvokeHTTP - API Call**

**Mục đích:** Gọi Football-Data.org API để lấy live matches

#### **Cấu hình Chi Tiết:**

| Property | Value | Giải thích |
|----------|-------|-----------|
| **HTTP Method** | `GET` | Method HTTP |
| **Remote URL** | `https://api.football-data.org/v4/matches` | API endpoint |
| **SSL Context Service** | `StandardSSLContextService` | Xử lý HTTPS |
| **Connection Timeout** | `30 sec` | Timeout kết nối |
| **Read Timeout** | `30 sec` | Timeout đọc data |
| **Attributes to Send** | (empty) | Không gửi attributes |
| **Include Date Header** | `true` | Thêm Date header |
| **Follow Redirects** | `true` | Follow 301/302 |
| **Put Response Body in Attribute** | (empty) | Response vào body (không phải attribute) |
| **Always Output Response** | `false` | Chỉ output khi success |
| **Add Response Headers to Request** | `false` | Không add headers |
| **Content-Type** | `application/json` | Content type |
| **Send Message Body** | `false` | GET không có body |

#### **Dynamic Properties (Headers):**
```properties
# Click (+) button to add dynamic properties

Property Name: X-Auth-Token
Property Value: ${FOOTBALL_API_TOKEN}

# Explanation: API key from .env file
# Set FOOTBALL_API_TOKEN as Process Group variable or use Parameter Context
```

#### **Query Parameters:**

**⚠️ LƯU Ý QUAN TRỌNG:**
API mặc định (không parameters) **TỰ ĐỘNG** trả về matches trong khoảng:
- `dateFrom`: Hôm nay
- `dateTo`: Ngày mai
- Bao gồm: TIMED, IN_PLAY, PAUSED, FINISHED

**✅ OPTION 1: MẶC ĐỊNH - Không cần parameters** ⭐ **RECOMMENDED (SIMPLEST)**
```properties
# Không thêm query parameters gì cả
# API tự động filter theo ngày

Property Name: query.limit
Property Value: 100
Description: Giới hạn số matches trả về (optional)
```

**Result URL:**
```
https://api.football-data.org/v4/matches?limit=100
```

**API tự động trả về:**
- ✅ FINISHED matches (đã kết thúc hôm nay)
- ✅ IN_PLAY matches (đang diễn ra)
- ✅ PAUSED matches (half-time)
- ✅ TIMED matches (sắp diễn ra hôm nay/ngày mai)

**Chỉ cần dùng RouteOnAttribute để filter:**
- **Keep:** IN_PLAY, PAUSED, FINISHED
- **Discard:** TIMED (chưa có score thật)

---

**OPTION 2: CHỈ LIVE MATCHES (Real-time only)**
```properties
Property Name: query.status
Property Value: IN_PLAY,PAUSED
Description: Chỉ lấy matches đang diễn ra

Property Name: query.limit
Property Value: 100
```

**Result URL:**
```
https://api.football-data.org/v4/matches?status=IN_PLAY,PAUSED&limit=100
```

**⚠️ Nhược điểm:** Sẽ **MẤT** lịch sử các trận FINISHED trong ngày

---

**OPTION 3: LIVE + FINISHED (Explicit filtering)**
```properties
Property Name: query.status
Property Value: IN_PLAY,PAUSED,FINISHED
Description: Lấy live + finished, bỏ TIMED

Property Name: query.limit
Property Value: 100
```

**Result URL:**
```
https://api.football-data.org/v4/matches?status=IN_PLAY,PAUSED,FINISHED&limit=100
```

**💡 Lợi ích:**
- ✅ API filtering → Giảm data processing
- ✅ Không nhận TIMED matches (không cần RouteOnAttribute filter)
- ✅ Có đầy đủ lịch sử trong ngày

---

**🎯 KHUYẾN NGHỊ: Dùng OPTION 1 (Mặc định)**

Vì:
1. ✅ **Đơn giản nhất** - Không cần config query params
2. ✅ API đã filter theo ngày tự động
3. ✅ Chỉ cần 1 RouteOnAttribute processor để lọc status
4. ✅ Có đầy đủ data: LIVE + FINISHED
5. ✅ Dễ maintain và debug

#### **Relationships:**
- **success** → Connect to EvaluateJsonPath
- **failure** → Connect to LogAttribute (log errors)
- **retry** → Auto-retry with backoff
- **no retry** → Connect to LogAttribute

#### **Cấu hình Retry:**
```properties
Settings Tab:
  Penalty Duration: 30 sec
  Yield Duration: 10 sec
  
# Nếu fail, sẽ retry sau 30 giây
```

---

### **3️⃣ EvaluateJsonPath - Parse JSON Response**

**Mục đích:** Extract dữ liệu từ JSON response của API

#### **Cấu hình:**

| Property | Value | Giải thích |
|----------|-------|-----------|
| **Destination** | `flowfile-attribute` | Lưu vào attributes (không phải content) |
| **Return Type** | `json` | Giữ nguyên format JSON |
| **Path Not Found Behavior** | `warn` | Cảnh báo nếu path không tồn tại |
| **Null Value Representation** | `empty string` | Null → "" |

#### **Dynamic Properties (JSON Paths):**

Click (+) để thêm các path cần extract:

```properties
Property Name: resultSet.count
Property Value: $.resultSet.count
Description: Tổng số matches trong result

Property Name: resultSet.played
Property Value: $.resultSet.played
Description: Số matches đã chơi (FINISHED)

Property Name: matches
Property Value: $.matches
Description: Array chứa tất cả matches (MAIN DATA)

Property Name: filters.dateFrom
Property Value: $.filters.dateFrom
Description: Filter date from (optional)

Property Name: resultSet.competitions
Property Value: $.resultSet.competitions
Description: List of competition codes
```

#### **Example Response Structure:**
```json
{
  "filters": {
    "dateFrom": "2025-11-26",
    "dateTo": "2025-11-27",
    "permission": "TIER_ONE"
  },
  "resultSet": {
    "count": 17,
    "competitions": "BSA,CL,ELC",
    "first": "2025-11-26",
    "last": "2025-11-26",
    "played": 2
  },
  "matches": [
    {
      "area": {
        "id": 2077,
        "name": "Europe",
        "code": "EUR",
        "flag": "https://crests.football-data.org/EUR.svg"
      },
      "competition": {
        "id": 2001,
        "name": "UEFA Champions League",
        "code": "CL",
        "type": "CUP",
        "emblem": "https://crests.football-data.org/CL.png"
      },
      "season": {
        "id": 2454,
        "startDate": "2025-09-16",
        "endDate": "2026-05-30",
        "currentMatchday": 5,
        "winner": null
      },
      "id": 551948,
      "utcDate": "2025-11-26T20:00:00Z",
      "status": "TIMED",
      "matchday": 5,
      "stage": "LEAGUE_STAGE",
      "group": null,
      "lastUpdated": "2025-11-26T01:32:00Z",
      "homeTeam": {
        "id": 64,
        "name": "Liverpool FC",
        "shortName": "Liverpool",
        "tla": "LIV",
        "crest": "https://crests.football-data.org/64.png"
      },
      "awayTeam": {
        "id": 674,
        "name": "PSV",
        "shortName": "PSV",
        "tla": "PSV",
        "crest": "https://crests.football-data.org/674.png"
      },
      "score": {
        "winner": null,
        "duration": "REGULAR",
        "fullTime": {
          "home": null,
          "away": null
        },
        "halfTime": {
          "home": null,
          "away": null
        }
      },
      "odds": {
        "msg": "Activate Odds-Package in User-Panel to retrieve odds."
      },
      "referees": []
    }
  ]
}
```

#### **Relationships:**
- **matched** → Connect to SplitJson
- **unmatched** → Connect to LogAttribute (log parsing errors)

---

### **4️⃣ SplitJson - Tách Array Thành FlowFiles**

**Mục đích:** Tách array `$.matches` thành từng FlowFile riêng cho mỗi match

#### **Cấu hình:**

| Property | Value | Giải thích |
|----------|-------|-----------|
| **JsonPath Expression** | `$.matches` | Path tới array cần split |
| **Null Value Representation** | `empty string` | Xử lý null |

#### **Hoạt động:**

**Input (1 FlowFile):**
```json
{
  "resultSet": {"count": 3, "played": 1},
  "matches": [
    {
      "id": 535290,
      "status": "FINISHED",
      "homeTeam": {"name": "CA Mineiro"},
      "score": {"fullTime": {"home": 1, "away": 1}}
    },
    {
      "id": 551948,
      "status": "TIMED",
      "homeTeam": {"name": "Liverpool FC"},
      "score": {"fullTime": {"home": null, "away": null}}
    },
    {
      "id": 552042,
      "status": "TIMED",
      "homeTeam": {"name": "Paphos FC"},
      "score": {"fullTime": {"home": null, "away": null}}
    }
  ]
}
```

**Output (3 FlowFiles):**
```json
FlowFile 1: {
  "id": 535290,
  "status": "FINISHED",
  "homeTeam": {"name": "CA Mineiro"},
  "score": {"fullTime": {"home": 1, "away": 1}}
}

FlowFile 2: {
  "id": 551948,
  "status": "TIMED",
  "homeTeam": {"name": "Liverpool FC"}
}

FlowFile 3: {
  "id": 552042,
  "status": "TIMED",
  "homeTeam": {"name": "Paphos FC"}
}
```

#### **Attributes Added:**
- `fragment.index` → Vị trí trong array (0, 1, 2...)
- `fragment.count` → Tổng số fragments
- `fragment.identifier` → UUID của original FlowFile
- `segment.original.filename` → Tên file gốc

#### **Relationships:**
- **split** → Connect to **UpdateAttribute** (BỎ QUA RouteOnAttribute!)
- **original** → Auto-terminate (không cần nữa)
- **failure** → Connect to LogAttribute

---

~~### **5️⃣ RouteOnAttribute - Lọc Live Matches**~~ **[REMOVED - KHÔNG CẦN NỮA]**

**❌ Processor này đã bị XÓA khỏi luồng!**

**Lý do:**
- Spark Streaming sẽ tự động **upsert** mọi message dựa trên `match_id`
- Không cần lọc status ở NiFi → Đơn giản hơn
- Capture **full lifecycle** của match: TIMED → IN_PLAY → PAUSED → FINISHED

~~**Mục đích:** Chỉ giữ lại matches có `status = "LIVE"`, discard các matches đã kết thúc~~

#### **Cấu hình:**

| Property | Value | Giải thích |
|----------|-------|-----------|
| **Routing Strategy** | `Route to Property name` | Route dựa trên property name |

#### **Dynamic Properties (Routing Rules):**

```properties
# Strategy 1: CHỈ LIVE MATCHES (real-time only)
Property Name: live_match
Property Value: ${status:equals('IN_PLAY')}
Description: Match đang diễn ra (IN_PLAY = đang chơi)

Property Name: paused_match
Property Value: ${status:equals('PAUSED')}
Description: Match đang tạm dừng (half-time)

# Strategy 2: BAO GỒM FINISHED (để có lịch sử trong ngày)
Property Name: finished_today
Property Value: ${status:equals('FINISHED')}
Description: Match đã kết thúc TRONG NGÀY (có score cuối cùng)

# Strategy 3: SCHEDULED (optional - để biết match sắp diễn ra)
Property Name: timed_match
Property Value: ${status:equals('TIMED')}
Description: Match chưa bắt đầu (scheduled)
```

**⚠️ QUAN TRỌNG - Data Strategy:**

**Nếu KHÔNG lấy FINISHED:**
- ✅ Chỉ có real-time events (IN_PLAY, PAUSED)
- ❌ MẤT lịch sử các trận đã kết thúc trong ngày
- ❌ Không thể phân tích kết quả trận đấu
- ❌ Dashboard chỉ hiển thị matches đang diễn ra

**Nếu LẤY CẢ FINISHED:**
- ✅ Có lịch sử đầy đủ trong ngày
- ✅ Có score cuối cùng của mọi trận
- ✅ Dashboard hiển thị cả past results
- ⚠️ Cần thêm logic: chỉ lấy FINISHED trong ngày (dùng `lastUpdated` hoặc `utcDate`)

**RECOMMENDED Strategy:**

```properties
# Route ALL relevant matches (IN_PLAY, PAUSED, FINISHED)
Property Name: relevant_match
Property Value: ${status:in('IN_PLAY', 'PAUSED', 'FINISHED')}
Description: Tất cả matches có giá trị (live + finished today)

# Then filter OUT old matches using timestamp
# Check if match is from TODAY only
```

**Các Status Values trong API:**
- `TIMED` - Match chưa bắt đầu (scheduled) → **SKIP** (chưa có data thật)
- `IN_PLAY` - Match đang diễn ra → **KEEP** ✅
- `PAUSED` - Match tạm dừng (half-time) → **KEEP** ✅
- `FINISHED` - Match đã kết thúc → **KEEP** ✅ (để có lịch sử)
- `POSTPONED` - Match bị hoãn → **SKIP** (không có data)
- `CANCELLED` - Match bị hủy → **SKIP** (không có data)
- `SUSPENDED` - Match bị tạm ngưng → **SKIP** (edge case)

#### **Expression Language:**

NiFi hỗ trợ Expression Language mạnh mẽ:

```java
// Basic equals
${match.status:equals('LIVE')}

// Contains
${match.status:contains('LIVE')}

// Or condition
${match.status:equals('LIVE'):or(${match.status:equals('IN_PLAY')})}

// And condition
${match.status:equals('LIVE'):and(${match.minute:gt(0)})}

// Not equals
${match.status:notEquals('FINISHED')}

// Check if exists
${match.status:isEmpty():not()}

// Numeric comparison
${match.minute:toNumber():ge(45)}  // minute >= 45
```

#### **Relationships:**
- **relevant_match** (IN_PLAY, PAUSED, FINISHED) → Connect to **RouteOnAttribute #2 (Date Filter)**
- **unmatched** (TIMED, POSTPONED, etc.) → Auto-terminate

---

### **5️⃣-B RouteOnAttribute #2 - Filter Matches by Date (Optional)**

**Mục đích:** Chỉ giữ matches TRONG NGÀY HÔM NAY (để không lấy FINISHED cũ)

#### **Cấu hình:**

| Property | Value | Giải thích |
|----------|-------|-----------|
| **Routing Strategy** | `Route to Property name` | Route dựa trên property name |

#### **Dynamic Properties (Date Filtering):**

```properties
# Option 1: Filter by utcDate (match date)
Property Name: today_match
Property Value: ${utcDate:toDate('yyyy-MM-dd'):format('yyyy-MM-dd'):equals(${now():format('yyyy-MM-dd')})}
Description: Check if match date = today

# Option 2: Filter by lastUpdated (recent updates only)
Property Name: recent_update
Property Value: ${lastUpdated:toDate('yyyy-MM-dd'):format('yyyy-MM-dd'):equals(${now():format('yyyy-MM-dd')})}
Description: Check if last update = today

# Option 3: Simple - Keep all (no date filter)
# Just route all relevant_match directly to UpdateAttribute
```

#### **Expression Language Examples:**

```java
// Check if match is TODAY
${utcDate:toDate('yyyy-MM-dd\'T\'HH:mm:ss\'Z\''):format('yyyy-MM-dd'):equals(${now():format('yyyy-MM-dd')})}

// Check if updated in last 24 hours
${lastUpdated:toNumber():gt(${now():toNumber():minus(86400000)})}
// 86400000 ms = 24 hours

// Check if match is within date range
${utcDate:toDate('yyyy-MM-dd\'T\'HH:mm:ss\'Z\''):toNumber():ge(${now():toNumber():minus(86400000)})}
```

#### **Relationships:**
- **today_match** → Connect to UpdateAttribute
- **recent_update** → Connect to UpdateAttribute  
- **unmatched** → Connect to LogAttribute (old matches, discard)

#### **⚠️ Lưu ý:**

**Nếu KHÔNG dùng Date Filter:**
- ✅ Đơn giản hơn (1 processor ít hơn)
- ⚠️ Sẽ lấy cả FINISHED cũ nếu API trả về
- 💡 **Khuyến nghị:** Dùng query parameter `dateFrom` và `dateTo` trong InvokeHTTP thay vì filter sau

**Nếu DÙNG Date Filter:**
- ✅ Chắc chắn chỉ có matches trong ngày
- ✅ Tránh duplicate data
- ⚠️ Thêm 1 processor (phức tạp hơn)

**RECOMMENDED: Dùng API Query Parameters thay vì processor filter**

```properties
# In InvokeHTTP Dynamic Properties:
Property Name: query.dateFrom
Property Value: ${now():format('yyyy-MM-dd')}

Property Name: query.dateTo
Property Value: ${now():format('yyyy-MM-dd')}
```

Với cách này, API chỉ trả về matches của ngày hôm nay → Không cần RouteOnAttribute #2!

---

### **6️⃣ UpdateAttribute - Enrich Metadata**

**Mục đích:** Thêm metadata và enrichment vào FlowFile

#### **Cấu hình Dynamic Properties:**

```properties
# Timestamp
Property Name: processing.timestamp
Property Value: ${now():format('yyyy-MM-dd HH:mm:ss')}
Description: Thời điểm xử lý

# Source
Property Name: data.source
Property Value: football-data-api
Description: Nguồn dữ liệu

# Event Type
Property Name: event.type
Property Value: live_match_update
Description: Loại event

# Kafka Key (để partition)
Property Name: kafka.key
Property Value: ${match.id}
Description: Dùng match ID làm Kafka key

# Topic
Property Name: kafka.topic
Property Value: live-match-events
Description: Kafka topic name

# Partition Strategy
Property Name: partition.key
Property Value: ${match.homeTeam.id:mod(3)}
Description: Distribute evenly across 3 partitions

# Processing ID
Property Name: processing.id
Property Value: ${UUID()}
Description: Unique processing ID

# Environment
Property Name: environment
Property Value: production
Description: Môi trường deploy
```

#### **Advanced Expression Examples:**

```java
// Conditional value
Property Name: match.importance
Property Value: ${match.competition.name:equals('Premier League'):ifElse('high', 'medium')}

// String manipulation
Property Name: match.display.name
Property Value: ${match.homeTeam.name} vs ${match.awayTeam.name}

// Date formatting
Property Name: match.date.formatted
Property Value: ${match.utcDate:format('yyyy-MM-dd HH:mm:ss', 'UTC')}

// Math operations
Property Name: match.elapsed.seconds
Property Value: ${match.minute:multiply(60)}

// Concatenation
Property Name: match.full.id
Property Value: ${match.competition.id}_${match.id}
```

---

### **7️⃣ JoltTransformJSON - Transform Schema**

**Mục đích:** Transform JSON schema từ Football-Data.org format sang Kafka message format

#### **Cấu hình:**

| Property | Value | Giải thích |
|----------|-------|-----------|
| **Jolt Transformation DSL** | `Chain` | Chạy nhiều transformations |
| **Jolt Specification** | (JSON spec below) | Chi tiết transformation |
| **Transform Cache Size** | `1` | Cache 1 spec (đủ) |

#### **Jolt Specification (JSON):**

```json
[
  {
    "operation": "shift",
    "spec": {
      "id": "match_id",
      "utcDate": "match_date",
      "status": "status",
      "minute": "minute",
      "injuryTime": "injury_time",
      "score": {
        "fullTime": {
          "home": "score.home",
          "away": "score.away"
        },
        "halfTime": {
          "home": "score.half_home",
          "away": "score.half_away"
        }
      },
      "homeTeam": {
        "id": "home_team_id",
        "name": "home_team_name",
        "shortName": "home_team_short",
        "tla": "home_team_tla",
        "crest": "home_team_crest"
      },
      "awayTeam": {
        "id": "away_team_id",
        "name": "away_team_name",
        "shortName": "away_team_short",
        "tla": "away_team_tla",
        "crest": "away_team_crest"
      },
      "competition": {
        "id": "competition_id",
        "name": "competition_name",
        "code": "competition_code",
        "type": "competition_type",
        "emblem": "competition_emblem"
      },
      "season": {
        "id": "season_id",
        "startDate": "season_start",
        "endDate": "season_end",
        "currentMatchday": "matchday"
      },
      "referees": "referees"
    }
  },
  {
    "operation": "default",
    "spec": {
      "minute": 0,
      "injury_time": 0,
      "processing_timestamp": "${now():toNumber()}",
      "source": "nifi-football-api",
      "version": "1.0"
    }
  },
  {
    "operation": "remove",
    "spec": {
      "competition": {
        "area": ""
      },
      "odds": "",
      "lastUpdated": ""
    }
  }
]
```

#### **Giải thích Jolt Operations:**

**1. SHIFT - Đổi tên và cấu trúc:**
```json
// Input
{
  "id": 441234,
  "homeTeam": {"name": "Arsenal"}
}

// Output (after shift)
{
  "match_id": 441234,
  "home_team_name": "Arsenal"
}
```

**2. DEFAULT - Thêm giá trị mặc định:**
```json
// Nếu field không tồn tại, thêm giá trị default
{
  "minute": 0,  // Default nếu minute = null
  "source": "nifi-football-api"
}
```

**3. REMOVE - Xóa fields không cần:**
```json
// Remove nested fields
{
  "competition": {
    "area": ""  // Remove this
  }
}
```

#### **Test Jolt Transformation:**

Có thể test online tại: https://jolt-demo.appspot.com/

**Input Example:**
```json
{
  "area": {
    "id": 2077,
    "name": "Europe",
    "code": "EUR",
    "flag": "https://crests.football-data.org/EUR.svg"
  },
  "competition": {
    "id": 2001,
    "name": "UEFA Champions League",
    "code": "CL",
    "type": "CUP",
    "emblem": "https://crests.football-data.org/CL.png"
  },
  "season": {
    "id": 2454,
    "startDate": "2025-09-16",
    "endDate": "2026-05-30",
    "currentMatchday": 5,
    "winner": null
  },
  "id": 551948,
  "utcDate": "2025-11-26T20:00:00Z",
  "status": "TIMED",
  "matchday": 5,
  "stage": "LEAGUE_STAGE",
  "group": null,
  "lastUpdated": "2025-11-26T01:32:00Z",
  "homeTeam": {
    "id": 64,
    "name": "Liverpool FC",
    "shortName": "Liverpool",
    "tla": "LIV",
    "crest": "https://crests.football-data.org/64.png"
  },
  "awayTeam": {
    "id": 674,
    "name": "PSV",
    "shortName": "PSV",
    "tla": "PSV",
    "crest": "https://crests.football-data.org/674.png"
  },
  "score": {
    "winner": null,
    "duration": "REGULAR",
    "fullTime": {"home": null, "away": null},
    "halfTime": {"home": null, "away": null}
  },
  "odds": {
    "msg": "Activate Odds-Package in User-Panel to retrieve odds."
  },
  "referees": []
}
```

**Output Example:**
```json
{
  "match_id": 551948,
  "match_date": "2025-11-26T20:00:00Z",
  "status": "TIMED",
  "matchday": 5,
  "stage": "LEAGUE_STAGE",
  "last_updated": "2025-11-26T01:32:00Z",
  "home_team_id": 64,
  "home_team_name": "Liverpool FC",
  "home_team_short": "Liverpool",
  "home_team_tla": "LIV",
  "home_team_crest": "https://crests.football-data.org/64.png",
  "away_team_id": 674,
  "away_team_name": "PSV",
  "away_team_short": "PSV",
  "away_team_tla": "PSV",
  "away_team_crest": "https://crests.football-data.org/674.png",
  "score": {
    "winner": null,
    "duration": "REGULAR",
    "home": null,
    "away": null,
    "half_home": null,
    "half_away": null
  },
  "competition_id": 2001,
  "competition_name": "UEFA Champions League",
  "competition_code": "CL",
  "competition_type": "CUP",
  "competition_emblem": "https://crests.football-data.org/CL.png",
  "season_id": 2454,
  "season_start": "2025-09-16",
  "season_end": "2026-05-30",
  "area_id": 2077,
  "area_name": "Europe",
  "area_code": "EUR",
  "referees": [],
  "processing_timestamp": 1732651200000,
  "source": "nifi-football-api",
  "version": "1.0"
}
```

---

### **8️⃣ PublishKafkaRecord - Gửi tới Confluent Cloud**

**Mục đích:** Publish transformed message tới Confluent Cloud Kafka

#### **Cấu hình:**

| Property | Value | Giải thích |
|----------|-------|-----------|
| **Kafka Brokers** | `${KAFKA_BOOTSTRAP_SERVERS}` | From Parameter Context |
| **Topic Name** | `live-match-events` | Kafka topic |
| **Record Reader** | `JsonTreeReader` | Parse JSON |
| **Record Writer** | `JsonRecordSetWriter` | Write JSON |
| **Use Transactions** | `false` | Không cần transaction |
| **Attributes to Send as Headers** | (regex) | Send metadata as headers |
| **Message Key Field** | `match_id` | Partition by match ID |
| **Delivery Guarantee** | `GUARANTEE_REPLICATED` | Đợi replicate xong |
| **Max Request Size** | `1 MB` | Max message size |
| **Acknowledgment Wait Time** | `30 sec` | Timeout |
| **Metadata Wait Time** | `30 sec` | Metadata timeout |
| **Partitioner class** | `DefaultPartitioner` | Default partition logic |
| **Compression Type** | `snappy` | Compress message |

#### **Security Properties:**

```properties
Security Protocol: SASL_SSL

SASL Mechanism: PLAIN

Username: ${KAFKA_API_KEY}

Password: ${KAFKA_API_SECRET}

SSL Context Service: StandardSSLContextService
```

#### **Advanced Properties:**

```properties
# Batching (performance optimization)
Max Batch Size: 16 KB
Batch Size: 16 KB

# Retry
Max Request Timeout: 30 sec

# Headers (send attributes as Kafka headers)
Attributes to Send as Headers (Regex): 
  processing\..*|data\.source|event\.type
  
# Explanation: Send all attributes starting with "processing." 
# and also send "data.source" and "event.type"
```

#### **Kafka Headers Example:**
```
Message Headers:
  processing.timestamp: 2025-11-26 20:00:00
  processing.id: 123e4567-e89b-12d3-a456-426614174000
  data.source: football-data-api
  event.type: live_match_update
  
Message Key: 441234

Message Value: {"match_id": 441234, ...}
```

#### **Relationships:**
- **success** → Connect to LogAttribute (log success)
- **failure** → Connect to LogAttribute (retry manually)

---

## 🎛️ Cấu Hình Controller Services

Controller Services là shared services được dùng bởi nhiều processors.

### **1. StandardSSLContextService**

**Mục đích:** Xử lý HTTPS connections

**Cấu hình:**

| Property | Value |
|----------|-------|
| **Truststore Filename** | (empty - use default Java cacerts) |
| **Truststore Password** | (empty) |
| **Truststore Type** | `JKS` |
| **TLS Protocol** | `TLS` |

**Enable Service:** Click ⚡ icon

---

### **2. JsonTreeReader**

**Mục đích:** Parse JSON content thành Records

**Cấu hình:**

| Property | Value |
|----------|-------|
| **Schema Access Strategy** | `Infer Schema` |
| **Schema Inference Cache** | (none) |
| **Max String Length** | `20 MB` |

**Enable Service:** Click ⚡ icon

---

### **3. JsonRecordSetWriter**

**Mục đích:** Write Records thành JSON

**Cấu hình:**

| Property | Value |
|----------|-------|
| **Schema Write Strategy** | `No Schema` |
| **Schema Access Strategy** | `Inherit Record Schema` |
| **Pretty Print JSON** | `false` (compact) |
| **Suppress Null Values** | `Never Suppress` |
| **Output Grouping** | `One Line Per Object` |

**Enable Service:** Click ⚡ icon

---

### **4. StandardRestrictedSSLContextService** (cho Kafka)

**Mục đích:** SSL cho Confluent Cloud connection

**Cấu hình:**

| Property | Value |
|----------|-------|
| **Truststore Filename** | (empty) |
| **Truststore Type** | `JKS` |
| **TLS Protocol** | `TLSv1.2` |

**Enable Service:** Click ⚡ icon

---

## 🔗 Kết Nối Giữa Các Processor

### **Connection Configuration:**

Mỗi connection giữa 2 processors cần cấu hình:

#### **1. Basic Settings:**
```
Name: API Response → Parse JSON
Source: InvokeHTTP
Destination: EvaluateJsonPath
For Relationships: success
```

#### **2. Queue Settings:**

| Setting | Recommended Value | Giải thích |
|---------|------------------|-----------|
| **FlowFile Expiration** | `0 sec` | Không expire |
| **Back Pressure Object Threshold** | `10000` | Stop nếu >10k messages |
| **Back Pressure Size Threshold** | `1 GB` | Stop nếu >1GB |
| **Load Balance Strategy** | `Do not load balance` | Single node |
| **Prioritizers** | `FirstInFirstOutPrioritizer` | FIFO |

#### **3. Advanced Settings:**
```
Bend Points: (none - straight line)
Labels: (optional - mô tả connection)
```

---

### **Connection Map:**

```
GenerateFlowFile [success]
    ↓
InvokeHTTP [success] ──→ EvaluateJsonPath
           [failure] ──→ LogAttribute (Error)
           [retry] ────→ (auto-retry)
           
EvaluateJsonPath [matched] ──→ SplitJson
                 [unmatched] ─→ LogAttribute (Parse Error)
                 
SplitJson [split] ────→ RouteOnAttribute
          [original] ─→ (auto-terminate)
          [failure] ──→ LogAttribute
          
RouteOnAttribute [live_match] ───→ UpdateAttribute
                 [in_play_match] ─→ UpdateAttribute
                 [paused_match] ──→ UpdateAttribute
                 [unmatched] ─────→ (auto-terminate)
                 
UpdateAttribute [success] ──→ JoltTransformJSON

JoltTransformJSON [success] ──→ PublishKafkaRecord
                  [failure] ──→ LogAttribute (Transform Error)
                  
PublishKafkaRecord [success] ──→ LogAttribute (Success)
                   [failure] ──→ LogAttribute (Kafka Error)
```

---

## 🎯 Best Practices

### **1. Error Handling:**

✅ **Luôn kết nối failure relationships:**
```
failure → LogAttribute → (optional) PutFile (lưu failed data)
```

✅ **Cấu hình Bulletin Level:**
```
Settings > Bulletin Level: WARN
→ Show warnings in UI
```

✅ **Enable Provenance:**
```
Settings > Automatically Record Provenance: true
→ Track data lineage
```

---

### **2. Performance Optimization:**

✅ **Concurrent Tasks:**
```
InvokeHTTP: 1 task (sequential API calls)
SplitJson: 2-4 tasks (parallel split)
PublishKafka: 2-4 tasks (parallel publish)
```

✅ **Batching:**
```
PublishKafka > Batch Size: 16 KB
→ Send multiple records in one request
```

✅ **Compression:**
```
PublishKafka > Compression Type: snappy
→ Reduce network traffic
```

---

### **3. Monitoring:**

✅ **Enable Statistics:**
```
Right-click canvas > Configure
Statistics > Enable: true
Refresh Interval: 30 sec
```

✅ **View Data Provenance:**
```
Right-click FlowFile > View Data Provenance
→ See full journey of data
```

✅ **Check Queue:**
```
Hover over connection → See queue size and data size
```

---

### **4. Security:**

✅ **Use Parameter Context:**
```
Right-click canvas > Parameters
Add Parameters:
  - KAFKA_BOOTSTRAP_SERVERS
  - KAFKA_API_KEY (Sensitive: true)
  - KAFKA_API_SECRET (Sensitive: true)
  - FOOTBALL_API_TOKEN (Sensitive: true)
```

✅ **Sensitive Property Encryption:**
```
NiFi automatically encrypts sensitive properties
using nifi.sensitive.props.key in nifi.properties
```

---

### **5. Testing:**

✅ **Test với Sample Data:**
```
1. Right-click GenerateFlowFile > Run Once
2. Right-click connection > List Queue
3. Click FlowFile > View Content
4. Verify JSON structure
```

✅ **Enable Debug Logging:**
```
Settings > Bulletin Level: DEBUG
Settings > Log Level: DEBUG (temporary)
```

---

## 🐛 Troubleshooting

### **❌ Problem: InvokeHTTP Returns 401 Unauthorized**

**Cause:** Invalid API token

**Solution:**
```bash
# Check API token
echo $FOOTBALL_API_TOKEN

# Test API manually
curl -H "X-Auth-Token: YOUR_TOKEN" \
  https://api.football-data.org/v4/matches?status=LIVE

# Update Parameter Context in NiFi
Right-click canvas > Parameters > Edit FOOTBALL_API_TOKEN
```

---

### **❌ Problem: PublishKafka Fails with "Connection Refused"**

**Cause:** Wrong Kafka bootstrap servers

**Solution:**
```bash
# Verify Confluent Cloud credentials
cat .env | grep KAFKA

# Test connection from terminal
telnet pkc-xxxxx.ap-southeast-1.aws.confluent.cloud 9092

# Update NiFi Parameter Context
KAFKA_BOOTSTRAP_SERVERS = correct value from .env
```

---

### **❌ Problem: SplitJson Produces No Output**

**Cause:** Wrong JsonPath expression

**Solution:**
```
1. Before SplitJson, add LogAttribute to see full JSON
2. Verify JSON structure in API response
3. Test JsonPath online: https://jsonpath.com/
4. Update SplitJson > JsonPath Expression
```

---

### **❌ Problem: Queue is Full (Backpressure)**

**Cause:** Downstream processor is slow

**Solution:**
```
1. Check which connection is full (red bar)
2. Increase concurrent tasks on slow processor
3. Adjust queue size:
   Right-click connection > Configure
   Back Pressure Object Threshold: 20000
```

---

### **❌ Problem: No Data Flowing (Zero Events)**

**Cause:** No live matches at the moment

**Solution:**
```bash
# Test API manually to verify
curl -H "X-Auth-Token: YOUR_TOKEN" \
  "https://api.football-data.org/v4/matches?status=LIVE"

# Response: {"count": 0, "matches": []}
# → This is normal if no live matches

# To test flow, change query parameter:
Property Name: query.status
Property Value: SCHEDULED
# → This will return upcoming matches
```

---

### **❌ Problem: Jolt Transform Fails**

**Cause:** Unexpected JSON structure

**Solution:**
```
1. View input JSON:
   Right-click connection before Jolt > List Queue
   Click FlowFile > View Content
   
2. Test Jolt spec online:
   https://jolt-demo.appspot.com/
   Copy input JSON and Jolt spec
   
3. Adjust Jolt spec in NiFi
4. Test again
```

---

## 📊 Monitoring Dashboard

### **Key Metrics to Monitor:**

| Metric | Location | Threshold |
|--------|----------|-----------|
| **API Call Success Rate** | InvokeHTTP > Tasks/5min | >95% |
| **Messages Published** | PublishKafka > Out | >0 when live matches |
| **Queue Size** | Connections | <1000 FlowFiles |
| **Processing Time** | Processor Stats | <5 sec average |
| **Error Rate** | Bulletin Board | <1% |

### **NiFi UI Locations:**

```
📊 Summary Tab (top):
  - Total FlowFiles
  - Total Queued
  - Total Data Queued
  
📊 Processor Stats (right-click):
  - Tasks/5min: Số lần chạy
  - In: FlowFiles vào
  - Out: FlowFiles ra
  - Read/Write: Data size
  - Tasks Duration: Thời gian xử lý
  
📊 Bulletin Board (top-right bell icon):
  - Warnings
  - Errors
  - Info messages
  
📊 Data Provenance (right-click FlowFile):
  - Full journey
  - Timestamps
  - Attributes at each step
  - Content changes
```

---

## 🎓 Advanced Topics

### **1. Process Groups (Organization):**

**Tạo Process Group:**
```
1. Drag "Process Group" icon to canvas
2. Name: "Live Match Ingestion"
3. Drag processors vào group
4. Double-click group to enter
5. Add Input Port và Output Port để connect với outside
```

**Benefits:**
- 📁 Organize complex flows
- 🔒 Apply security at group level
- 📊 Group-level monitoring
- 🔄 Reusable templates

---

### **2. Templates (Reusability):**

**Export Template:**
```
1. Select all processors (Ctrl+A)
2. Right-click > Create Template
3. Name: "Football API to Kafka"
4. Download: NiFi UI > Templates > Export
```

**Import Template:**
```
1. NiFi UI > Upload Template
2. Drag Template icon to canvas
3. Select template
4. Configure parameters
```

---

### **3. Parameter Contexts (Configuration Management):**

**Best Practice Structure:**
```yaml
Context Name: Football-API-Config

Parameters:
  # API
  - FOOTBALL_API_URL: https://api.football-data.org/v4
  - FOOTBALL_API_TOKEN: (Sensitive)
  - API_POLL_INTERVAL: 30 sec
  
  # Kafka
  - KAFKA_BOOTSTRAP_SERVERS: (Sensitive)
  - KAFKA_API_KEY: (Sensitive)
  - KAFKA_API_SECRET: (Sensitive)
  - KAFKA_TOPIC: live-match-events
  
  # Processing
  - BATCH_SIZE: 16 KB
  - TIMEOUT: 30 sec
  - RETRY_BACKOFF: 30 sec
```

**Apply to Process Group:**
```
Right-click Process Group > Configure
General > Process Group Parameter Context
Select: Football-API-Config
```

---

### **4. Variables (Runtime Values):**

**Use Variables in Expression Language:**
```java
# In processor properties:
${KAFKA_TOPIC}
${API_POLL_INTERVAL}
${now():format('yyyy-MM-dd')}

# Nested variables:
${${environment}.kafka.servers}
# If environment=prod → ${prod.kafka.servers}
```

---

## 🚀 Deployment Checklist

- [ ] **1. Controller Services Enabled**
  - StandardSSLContextService ⚡
  - JsonTreeReader ⚡
  - JsonRecordSetWriter ⚡
  - StandardRestrictedSSLContextService ⚡

- [ ] **2. Parameter Context Configured**
  - FOOTBALL_API_TOKEN set
  - KAFKA_BOOTSTRAP_SERVERS set
  - KAFKA_API_KEY set (Sensitive)
  - KAFKA_API_SECRET set (Sensitive)

- [ ] **3. All Relationships Connected**
  - No yellow warning icons
  - All failure paths handled

- [ ] **4. Processors Configured**
  - Scheduling strategy set
  - Concurrent tasks appropriate
  - Properties validated

- [ ] **5. Security**
  - Sensitive values encrypted
  - SSL enabled for HTTPS/Kafka
  - Authentication configured

- [ ] **6. Testing**
  - Run Once to test
  - Verify data in Kafka
  - Check PostgreSQL for results
  - Monitor for 5-10 minutes

- [ ] **7. Monitoring**
  - Bulletin Level: WARN
  - Statistics enabled
  - Alerts configured (if needed)

---

## 📚 Tài Liệu Tham Khảo

### **NiFi Official:**
- [NiFi User Guide](https://nifi.apache.org/docs.html)
- [Expression Language Guide](https://nifi.apache.org/docs/nifi-docs/html/expression-language-guide.html)
- [Processor Documentation](https://nifi.apache.org/docs/nifi-docs/components/)

### **Jolt Transform:**
- [Jolt GitHub](https://github.com/bazaarvoice/jolt)
- [Jolt Online Tester](https://jolt-demo.appspot.com/)
- [Jolt Tutorial](https://community.cloudera.com/t5/Community-Articles/Jolt-quick-reference-for-Nifi-Jolt-Processors/ta-p/244350)

### **Kafka:**
- [Confluent Cloud Docs](https://docs.confluent.io/cloud/current/)
- [Kafka Security](https://docs.confluent.io/cloud/current/client-apps/config-client.html)

---

## ✅ Summary

Bạn đã học:
1. ✅ Thiết kế flow với 8 processors (+ optional date filter)
2. ✅ Cấu hình chi tiết từng processor
3. ✅ Expression Language và routing logic
4. ✅ Jolt transformation với real API structure
5. ✅ Kafka integration với Confluent Cloud
6. ✅ Error handling và monitoring
7. ✅ Best practices và optimization
8. ✅ Troubleshooting common issues
9. ✅ **Data strategy: Live + History trong ngày**

---

## 🎯 Recommended Configuration Summary

### **⚡ KHÁM PHÁ QUAN TRỌNG:**
API Football-Data.org **MẶC ĐỊNH** đã filter theo ngày rồi!
- Không cần parameters `dateFrom` / `dateTo`
- API tự động trả về matches từ hôm nay đến ngày mai
- Bao gồm: TIMED, IN_PLAY, PAUSED, FINISHED

### **InvokeHTTP Query Parameters (SIMPLIFIED):**
```
# KHÔNG CẦN query parameters cho date!
# Chỉ cần thêm limit (optional)

limit: 100
```

**Hoặc nếu muốn filter ngay từ API:**
```
status: IN_PLAY,PAUSED,FINISHED
limit: 100
```

### **RouteOnAttribute Filter:**
```
Keep: IN_PLAY, PAUSED, FINISHED
Discard: TIMED, POSTPONED, CANCELLED, SUSPENDED
```

**💡 Lý do:** API đã filter date tự động, chỉ cần filter status!

### **Data Flow:**
```
API (today's matches)
    ↓
IN_PLAY matches ────────→ Kafka (real-time updates)
PAUSED matches ─────────→ Kafka (half-time status)
FINISHED matches ───────→ Kafka (final results)
TIMED matches ──────────→ Discard (no data yet)
```

### **Benefits:**
- ✅ Real-time live scores (IN_PLAY, PAUSED)
- ✅ Lịch sử đầy đủ trong ngày (FINISHED)
- ✅ Dashboard hiển thị cả live + past results
- ✅ Analytics trên toàn bộ matches trong ngày
- ✅ API filtering → Giảm data processing

---

## 📊 Dashboard Use Cases

**1. Live Scoreboard:**
- Filter: `status = 'IN_PLAY' OR status = 'PAUSED'`
- Update: Real-time (30 sec refresh)

**2. Today's Results:**
- Filter: `status = 'FINISHED' AND date = today`
- Display: Final scores

**3. Full Day Summary:**
- All matches: FINISHED + IN_PLAY + PAUSED
- Show: Win/Loss/Draw stats

**4. Competition View:**
- Group by: competition_name
- Show: All matches per competition

---

## 🚀 Next Steps

1. **🔧 Implement in NiFi:**
   ```bash
   # Start NiFi
   cd /opt/nifi && ./bin/nifi.sh start
   
   # Access UI
   https://localhost:8443/nifi
   ```

2. **⚙️ Configure Processors:**
   - Follow processor order: 1 → 8
   - Set Parameter Context (API keys)
   - Enable Controller Services

3. **🧪 Test Flow:**
   ```bash
   # Run Once to test
   Right-click GenerateFlowFile > Run Once
   
   # Check queue
   Right-click connection > List Queue
   
   # View data
   Click FlowFile > View Content
   ```

4. **📊 Setup Superset:**
   ```bash
   # Start Superset
   source superset_venv/bin/activate
   superset run -p 8088
   
   # Connect to PostgreSQL
   Database: streaming.live_events
   ```

5. **✅ Verify Complete Pipeline:**
   ```bash
   # Check Kafka messages
   kafka-console-consumer --bootstrap-server YOUR_BOOTSTRAP \
     --topic live-match-events --from-beginning
   
   # Check PostgreSQL
   psql -U football_user -d football_analytics
   SELECT COUNT(*) FROM streaming.live_events;
   
   # Check Superset dashboard
   http://localhost:8088
   ```

---

## � Quick Reference

**API Status Values:**
- `IN_PLAY` → Match đang diễn ra ✅ KEEP
- `PAUSED` → Half-time ✅ KEEP
- `FINISHED` → Đã kết thúc ✅ KEEP
- `TIMED` → Chưa bắt đầu ❌ DISCARD

**Expression Language:**
```java
${status:equals('IN_PLAY')}
${status:in('IN_PLAY', 'PAUSED', 'FINISHED')}
${now():format('yyyy-MM-dd')}
${match.id:mod(3)}
```

**Connection Settings:**
- Back Pressure: 10,000 objects / 1 GB
- Expiration: 0 sec (no expire)
- Prioritizer: FirstInFirstOutPrioritizer

**Kafka Settings:**
- Security: SASL_SSL
- Mechanism: PLAIN
- Compression: snappy
- Batch Size: 16 KB

---

**🎉 Chúc bạn thành công với NiFi pipeline! 🚀**

**Có vấn đề gì, check lại:**
1. `NIFI_SETUP_GUIDE.md` - Detailed setup
2. `CONFLUENT_CLOUD_SETUP.md` - Kafka config
3. `SUPERSET_SETUP.md` - Dashboard setup
4. `LOCAL_SETUP.md` - Local installation guide

## Artifacts (DDL & Spark upsert)

- `schema/create_football_matches.sql` — Postgres DDL for the normalized `football_matches` table. Contains indexes and an example upsert (INSERT ... ON CONFLICT).
- `src/streaming/spark_upsert_matches.py` — Spark Structured Streaming skeleton that reads the `football-matches` Kafka topic, writes a staging table and performs upsert into Postgres using `INSERT ... ON CONFLICT`.

Quick notes:
- The Spark job expects these environment variables: `KAFKA_BOOTSTRAP`, `KAFKA_API_KEY`, `KAFKA_API_SECRET`, `POSTGRES_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- Run the DDL first to create the main table (and optionally create a staging table `football_matches_staging`).
- Typical run: use `spark-submit` with the Kafka package and the PostgreSQL JDBC driver.
