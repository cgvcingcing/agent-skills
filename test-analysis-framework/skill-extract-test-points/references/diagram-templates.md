# Mermaid 图表模板库

本文档提供常用的 Mermaid 图表模板，用于可视化需求分析结果。

---

## 1. 功能模块结构图（树图/思维导图）

**适用场景**：展示系统的功能模块层级结构

### 模板 1：横向树图
```mermaid
graph LR
    A[系统名称] --> B[模块1]
    A --> C[模块2]
    A --> D[模块3]
    B --> E[子功能1-1]
    B --> F[子功能1-2]
    C --> G[子功能2-1]
    C --> H[子功能2-2]
```

### 模板 2：纵向树图
```mermaid
graph TD
    A[系统名称]
    A --> B[模块1]
    A --> C[模块2]
    A --> D[模块3]
    B --> E[子功能1-1]
    B --> F[子功能1-2]
    C --> G[子功能2-1]
    D --> H[子功能3-1]
```

### 模板 3：带样式的树图
```mermaid
graph TD
    A[系统名称]:::root --> B[核心模块]:::core
    A --> C[辅助模块]:::support
    B --> D[功能1]:::feature
    B --> E[功能2]:::feature
    C --> F[功能3]:::feature
    
    classDef root fill:#4A90E2,stroke:#333,stroke-width:4px,color:#fff
    classDef core fill:#7ED321,stroke:#333,stroke-width:2px,color:#fff
    classDef support fill:#F5A623,stroke:#333,stroke-width:2px,color:#fff
    classDef feature fill:#D0E1F9,stroke:#333,stroke-width:1px
```

---

## 2. 业务流程图（流程图）

**适用场景**：展示业务流程的步骤和分支

### 模板 1：基础流程图
```mermaid
flowchart LR
    开始 --> 步骤1
    步骤1 --> 步骤2
    步骤2 --> 判断{条件?}
    判断 -->|是| 成功
    判断 -->|否| 失败
    失败 --> 结束
    成功 --> 结束
```

### 模板 2：纵向流程图（适合长流程）
```mermaid
flowchart TD
    Start([开始]) --> Input[用户输入]
    Input --> Validate{校验通过?}
    Validate -->|否| Error[显示错误]
    Error --> Input
    Validate -->|是| Process[业务处理]
    Process --> Save[保存数据]
    Save --> Success{成功?}
    Success -->|是| Notify[发送通知]
    Success -->|否| Retry{重试?}
    Retry -->|是| Process
    Retry -->|否| Fail[失败提示]
    Notify --> End([结束])
    Fail --> End
```

### 模板 3：泳道式流程图（多角色）
```mermaid
flowchart TD
    subgraph 用户
        A1[发起请求]
        A2[查看结果]
    end
    subgraph 系统
        B1[接收请求]
        B2[业务处理]
        B3[返回结果]
    end
    subgraph 数据库
        C1[查询数据]
        C2[保存数据]
    end
    
    A1 --> B1
    B1 --> B2
    B2 --> C1
    C1 --> C2
    C2 --> B3
    B3 --> A2
```

---

## 3. 接口调用链路图（时序图）

**适用场景**：展示 App/前端 → Node 聚合 → 服务端的调用关系

### 模板 1：基础时序图
```mermaid
sequenceDiagram
    participant App
    participant Node聚合
    participant 服务端
    
    App->>Node聚合: 请求接口
    Node聚合->>服务端: 调用服务
    服务端-->>Node聚合: 返回结果
    Node聚合-->>App: 返回数据
```

### 模板 2：带错误处理的时序图
```mermaid
sequenceDiagram
    participant App
    participant Node
    participant 用户服务
    participant 订单服务
    
    App->>+Node: POST /order/create
    Node->>+用户服务: GET /user/info
    用户服务-->>-Node: 用户信息
    
    alt 用户有效
        Node->>+订单服务: POST /order/create
        订单服务-->>-Node: 订单ID
        Node-->>App: 成功 {orderId: 123}
    else 用户无效
        Node-->>App: 错误 {code: 401}
    end
```

### 模板 3：并行调用时序图
```mermaid
sequenceDiagram
    participant App
    participant Node
    participant 服务A
    participant 服务B
    
    App->>Node: 请求聚合数据
    
    par 并行调用
        Node->>服务A: 调用A
        服务A-->>Node: 返回A
    and
        Node->>服务B: 调用B
        服务B-->>Node: 返回B
    end
    
    Node->>Node: 聚合数据
    Node-->>App: 返回结果
```

---

## 4. 状态转换图（状态图）

**适用场景**：展示数据的生命周期和状态流转

### 模板 1：基础状态图
```mermaid
stateDiagram-v2
    [*] --> 待提交
    待提交 --> 待审核: 提交
    待审核 --> 审核通过: 通过
    待审核 --> 审核驳回: 驳回
    审核驳回 --> 待提交: 修改后重新提交
    审核通过 --> [*]
```

### 模板 2：复杂状态图（订单状态）
```mermaid
stateDiagram-v2
    [*] --> 待支付
    待支付 --> 已支付: 支付成功
    待支付 --> 已取消: 超时/用户取消
    已支付 --> 已发货: 商家发货
    已发货 --> 已收货: 用户确认
    已发货 --> 退货中: 用户申请退货
    退货中 --> 已退货: 退货成功
    已收货 --> [*]
    已取消 --> [*]
    已退货 --> [*]
```

### 模板 3：带备注的状态图
```mermaid
stateDiagram-v2
    [*] --> 草稿
    草稿 --> 待审核: 提交审核
    
    state 待审核 {
        [*] --> 一审
        一审 --> 二审: 一审通过
        二审 --> [*]: 二审通过
    }
    
    待审核 --> 已发布: 审核通过
    待审核 --> 草稿: 驳回
    已发布 --> [*]
    
    note right of 待审核
        审核流程：
        1. 一审：部门主管
        2. 二审：总监
    end note
```

---

## 5. 数据流转图（Graph）

**适用场景**：展示数据在不同模块间的流转

### 模板 1：基础数据流图
```mermaid
graph LR
    A[用户输入] --> B[前端校验]
    B --> C[后端校验]
    C --> D[业务处理]
    D --> E[数据存储]
    E --> F[返回结果]
```

### 模板 2：分层数据流图
```mermaid
graph TB
    subgraph 展示层
        A1[页面展示]
    end
    subgraph 应用层
        B1[接口]
        B2[业务逻辑]
    end
    subgraph 数据层
        C1[数据库]
        C2[缓存]
    end
    
    A1 --> B1
    B1 --> B2
    B2 --> C1
    B2 --> C2
    C1 --> B2
    C2 --> B2
    B2 --> B1
    B1 --> A1
```

---

## 6. ER 图（实体关系图）

**适用场景**：展示数据库表结构和关系

### 模板 1：基础 ER 图
```mermaid
erDiagram
    用户 ||--o{ 订单 : 创建
    订单 ||--|{ 订单明细 : 包含
    商品 ||--o{ 订单明细 : 属于
    
    用户 {
        int id PK
        string name
        string email
    }
    订单 {
        int id PK
        int user_id FK
        datetime created_at
        decimal total_amount
    }
    订单明细 {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        decimal price
    }
    商品 {
        int id PK
        string name
        decimal price
    }
```

---

## 7. 甘特图（项目进度）

**适用场景**：展示测试计划和进度

### 模板 1：测试阶段甘特图
```mermaid
gantt
    title 测试计划
    dateFormat  YYYY-MM-DD
    section 测试准备
    需求分析           :done,    des1, 2026-09-01, 2d
    用例设计           :done,    des2, after des1, 3d
    环境搭建           :active,  des3, after des2, 2d
    section 测试执行
    功能测试           :         test1, after des3, 5d
    集成测试           :         test2, after test1, 3d
    回归测试           :         test3, after test2, 2d
    section 测试报告
    缺陷修复           :         fix1, after test3, 3d
    测试报告           :         report1, after fix1, 1d
```

---

## 8. 饼图（覆盖度统计）

**适用场景**：展示测试点分布或优先级分布

### 模板 1：优先级分布饼图
```mermaid
pie title 测试点优先级分布
    "P0 核心" : 15
    "P1 主要" : 35
    "P2 次要" : 30
    "P3 边缘" : 20
```

### 模板 2：功能维度分布饼图
```mermaid
pie title 测试点功能维度分布
    "主流程" : 20
    "核心功能" : 30
    "交互功能" : 25
    "常用功能" : 15
    "辅助功能" : 10
```

---

## 9. 类图（面向对象）

**适用场景**：展示系统架构或模块关系

### 模板 1：简单类图
```mermaid
classDiagram
    class 用户 {
        +String name
        +String email
        +login()
        +logout()
    }
    class 订单 {
        +int orderId
        +Date createTime
        +create()
        +cancel()
    }
    用户 "1" --> "*" 订单 : 创建
```

---

## 10. Git 图（分支流程）

**适用场景**：展示开发分支和发布流程

### 模板 1：Git Flow
```mermaid
gitgraph
    commit
    branch develop
    checkout develop
    commit
    branch feature/login
    checkout feature/login
    commit
    commit
    checkout develop
    merge feature/login
    checkout main
    merge develop
    commit tag: "v1.0"
```

---

## 使用建议

### 根据需求类型选择图表

| 需求特征 | 推荐图表 |
|---------|---------|
| 包含功能模块划分 | 功能模块结构图（树图） |
| 包含多步骤流程 | 业务流程图（流程图） |
| 包含接口调用 | 接口调用链路图（时序图） |
| 包含状态变化 | 状态转换图（状态图） |
| 包含数据流转 | 数据流转图（Graph） |
| 包含数据库表 | ER 图 |
| 包含统计分布 | 饼图 |

### 图表组合建议

**完整的测试点分析报告通常包含**：
1. 功能模块结构图（必须）
2. 业务流程图（如有流程）
3. 接口调用链路图（如有接口）
4. 状态转换图（如有状态）
5. 测试点分布饼图（统计用）

---

**最后更新**：2026-09-08
