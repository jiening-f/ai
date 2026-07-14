## 任务：数据库 Schema 设计

### 目标
设计并创建完整的数据库 Schema，包含建表 SQL 和对应的 SQLAlchemy 模型。

### 工作目录
`database/`

### 要求

1. **6 张核心表**

   - **games** — 游戏配置
     - id (INTEGER PK), name (TEXT), window_title (TEXT), window_class (TEXT), created_at, updated_at

   - **presets** — 预设配置
     - id (INTEGER PK), game_id (FK→games), name (TEXT), description (TEXT), flow_data (JSON/TEXT), is_active (BOOLEAN), created_at, updated_at

   - **executions** — 执行记录
     - id (INTEGER PK), preset_id (FK→presets), status (TEXT: running/paused/completed/stopped/error), started_at, finished_at, duration_ms, error_message (TEXT)

   - **execution_steps** — 执行步骤日志
     - id (INTEGER PK), execution_id (FK→executions), step_order (INTEGER), node_id (TEXT), node_type (TEXT), status (TEXT), input_data (JSON/TEXT), output_data (JSON/TEXT), started_at, finished_at

   - **plugins** — 插件
     - id (INTEGER PK), name (TEXT), version (TEXT), author (TEXT), description (TEXT), file_path (TEXT), enabled (BOOLEAN), installed_at

   - **settings** — 系统设置
     - key (TEXT UNIQUE PK), value (TEXT), updated_at

2. **产出文件**
   ```
   database/
   ├── schema.sql           # 完整建表 SQL（含索引）
   ├── models.py            # SQLAlchemy ORM 模型（与后端模型对齐）
   └── seeds/
       └── default_settings.sql  # 默认系统设置数据
   ```

3. **要求**
   - 所有表都要有 created_at / updated_at 时间戳
   - presets.flow_data 存储 JSON 格式的节点流程数据
   - 外键关系正确
   - 索引建在常用查询字段上

4. **验证**
   - SQL 可以直接在 SQLite 中执行无报错
   - SQLAlchemy 模型可以创建表

### 参考架构
详见 `docs/architecture.md` 第五节数据库设计。
