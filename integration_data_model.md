# 选课模拟系统与课程评价系统数据模型整合方案

## 项目背景

本文档设计了同济大学选课模拟系统与课程评价系统的数据模型整合方案，旨在将两个系统的数据统一管理，提供完整的课程信息和评价体系。

## 系统分析

### 选课模拟系统（exist_db_schema.sql）

**核心实体:**
- **coursedetail**: 课程详情（主表）
- **teacher**: 教师信息
- **major**: 专业信息
- **campus/faculty/calendar/language/assessment/coursenature**: 基础字典表

**特点:**
- 以选课信息为核心，包含完整的课程安排数据
- 支持学期、校区、开课单位等维度的筛选
- 包含选课人数、学分、周学时等选课相关信息

### 课程评价系统（jCourse后端）

**核心实体:**
- **Course**: 课程主体
- **Review**: 课程评价
- **Teacher**: 教师信息
- **Department/Category/Semester**: 基础信息

**特点:**
- 以课程评价为核心，支持用户评分和评论
- 包含详细的评价统计和反馈机制
- 支持全文搜索和智能推荐

## 数据模型整合设计

### 1. 统一课程模型

```sql
-- 统一课程表（整合coursedetail和Course）
CREATE TABLE `unified_course` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `course_code` VARCHAR(32) NOT NULL,           -- 统一课程代码
  `course_name` VARCHAR(255) NOT NULL,          -- 课程名称
  `credit` DOUBLE DEFAULT NULL,                 -- 学分

  -- 来自选课系统的字段
  `period` INT DEFAULT NULL,                    -- 学时
  `week_hour` INT DEFAULT NULL,                 -- 周学时
  `start_week` INT DEFAULT NULL,                -- 开始周
  `end_week` INT DEFAULT NULL,                  -- 结束周
  `enroll_number` INT DEFAULT NULL,             -- 选课人数
  `elc_number` INT DEFAULT NULL,                -- 实际选课人数

  -- 来自评价系统的字段
  `review_count` INT DEFAULT 0,                 -- 评价数量
  `review_avg` DOUBLE DEFAULT 0,                -- 平均评分
  `moderator_remark` TEXT,                      -- 管理员备注

  -- 共同字段
  `main_teacher_id` BIGINT,                     -- 主讲教师ID
  `department_id` INT,                          -- 开课单位ID
  `semester_id` INT,                            -- 学期ID
  `campus_id` VARCHAR(255),                     -- 校区ID
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_teacher_semester` (`course_code`, `main_teacher_id`, `semester_id`),
  KEY `idx_course_code` (`course_code`),
  KEY `idx_course_name` (`course_name`),
  KEY `idx_teacher` (`main_teacher_id`),
  KEY `idx_department` (`department_id`),
  KEY `idx_semester` (`semester_id`),
  KEY `idx_review_stats` (`review_count`, `review_avg`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2. 统一教师模型

```sql
-- 统一教师表（整合两系统的teacher表）
CREATE TABLE `unified_teacher` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `teacher_code` VARCHAR(32) UNIQUE,            -- 教师工号
  `teacher_name` VARCHAR(255) NOT NULL,         -- 教师姓名
  `department_id` INT,                          -- 所属单位
  `title` VARCHAR(64),                          -- 职称
  `pinyin` VARCHAR(64),                         -- 拼音（用于搜索）
  `abbr_pinyin` VARCHAR(64),                    -- 拼音简写
  `arrange_info` MEDIUMTEXT,                    -- 授课安排信息
  `last_semester_id` INT,                       -- 最后更新学期
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_teacher_code_name` (`teacher_code`, `teacher_name`),
  KEY `idx_teacher_name` (`teacher_name`),
  KEY `idx_department` (`department_id`),
  KEY `idx_pinyin` (`pinyin`, `abbr_pinyin`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3. 统一基础信息表

```sql
-- 统一开课单位表
CREATE TABLE `unified_department` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(64),                           -- 单位代码
  `name` VARCHAR(255) NOT NULL,                 -- 单位名称
  `name_i18n` VARCHAR(255),                     -- 国际化名称
  `type` ENUM('faculty', 'department') DEFAULT 'department', -- 单位类型
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dept_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 统一学期表
CREATE TABLE `unified_semester` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `calendar_id` INT,                            -- 对应原系统的calendarId
  `name` VARCHAR(64) NOT NULL,                  -- 学期名称
  `name_i18n` VARCHAR(255),                     -- 国际化名称
  `available` BOOLEAN DEFAULT TRUE,             -- 是否可用
  `start_date` DATE,                            -- 开始日期
  `end_date` DATE,                              -- 结束日期
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_semester_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 统一校区表
CREATE TABLE `unified_campus` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(255) NOT NULL,                 -- 校区代码
  `name` VARCHAR(255) NOT NULL,                 -- 校区名称
  `name_i18n` VARCHAR(255),                     -- 国际化名称
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_campus_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 课程性质/类别表
CREATE TABLE `unified_course_category` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `label_id` INT,                               -- 对应原系统的courseLabelId
  `name` VARCHAR(255) NOT NULL,                 -- 类别名称
  `description` TEXT,                           -- 类别描述
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_category_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4. 课程评价相关表

```sql
-- 课程评价表（基于jCourse的Review模型）
CREATE TABLE `course_review` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,                    -- 用户ID
  `course_id` BIGINT NOT NULL,                  -- 课程ID
  `semester_id` INT,                            -- 上课学期
  `rating` INT NOT NULL,                        -- 评分（1-5）
  `comment` TEXT,                               -- 详细评论
  `score` VARCHAR(10),                          -- 成绩
  `approve_count` INT DEFAULT 0,                -- 赞同数
  `disapprove_count` INT DEFAULT 0,             -- 反对数
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `modified_at` TIMESTAMP NULL,
  `moderator_remark` TEXT,                      -- 管理员备注
  `search_vector` TEXT,                         -- 全文搜索向量

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_course` (`user_id`, `course_id`),
  KEY `idx_course` (`course_id`),
  KEY `idx_rating` (`rating`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_review_course` FOREIGN KEY (`course_id`) REFERENCES `unified_course` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 评价反馈表
CREATE TABLE `review_reaction` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `review_id` BIGINT NOT NULL,
  `reaction` TINYINT DEFAULT 0,                 -- 0:重置 1:赞同 -1:反对
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_review` (`user_id`, `review_id`),
  CONSTRAINT `fk_reaction_review` FOREIGN KEY (`review_id`) REFERENCES `course_review` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 5. 关联关系表

```sql
-- 课程与类别关联表
CREATE TABLE `course_category_relation` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `course_id` BIGINT NOT NULL,
  `category_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_category` (`course_id`, `category_id`),
  CONSTRAINT `fk_ccr_course` FOREIGN KEY (`course_id`) REFERENCES `unified_course` (`id`),
  CONSTRAINT `fk_ccr_category` FOREIGN KEY (`category_id`) REFERENCES `unified_course_category` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 课程与教师关联表（教师组）
CREATE TABLE `course_teacher_relation` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `course_id` BIGINT NOT NULL,
  `teacher_id` BIGINT NOT NULL,
  `is_main_teacher` BOOLEAN DEFAULT FALSE,      -- 是否为主讲教师
  `role` VARCHAR(64),                           -- 教师角色
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_teacher` (`course_id`, `teacher_id`),
  CONSTRAINT `fk_ctr_course` FOREIGN KEY (`course_id`) REFERENCES `unified_course` (`id`),
  CONSTRAINT `fk_ctr_teacher` FOREIGN KEY (`teacher_id`) REFERENCES `unified_teacher` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 专业与课程关联表
CREATE TABLE `major_course_relation` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `major_id` INT NOT NULL,
  `course_id` BIGINT NOT NULL,
  `is_required` BOOLEAN DEFAULT FALSE,          -- 是否为必修课
  `credit_requirement` DOUBLE,                  -- 学分要求
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_major_course` (`major_id`, `course_id`),
  CONSTRAINT `fk_mcr_course` FOREIGN KEY (`course_id`) REFERENCES `unified_course` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 数据迁移策略

### 1. 基础数据迁移

```sql
-- 迁移校区数据
INSERT INTO unified_campus (code, name, name_i18n)
SELECT campus, campus, campusI18n FROM campus;

-- 迁移开课单位数据
INSERT INTO unified_department (name, name_i18n, type)
SELECT faculty, facultyI18n, 'faculty' FROM faculty
UNION
SELECT name, name, 'department' FROM jcourse_api_department;

-- 迁移学期数据
INSERT INTO unified_semester (calendar_id, name, name_i18n)
SELECT calendarId, CAST(calendarId AS CHAR), calendarIdI18n FROM calendar
UNION
SELECT NULL, name, name FROM jcourse_api_semester;
```

### 2. 教师数据整合

```sql
-- 整合教师数据（优先使用评价系统的详细信息）
INSERT INTO unified_teacher (teacher_code, teacher_name, department_id, title, pinyin, abbr_pinyin)
SELECT
  COALESCE(t1.teacherCode, t2.tid) as teacher_code,
  COALESCE(t2.name, t1.teacherName) as teacher_name,
  d.id as department_id,
  t2.title,
  t2.pinyin,
  t2.abbr_pinyin
FROM teacher t1
FULL OUTER JOIN jcourse_api_teacher t2 ON t1.teacherName = t2.name
LEFT JOIN unified_department d ON d.name = t2.department_name;
```

### 3. 课程数据整合

```sql
-- 整合课程数据
INSERT INTO unified_course (
  course_code, course_name, credit, period, week_hour, start_week, end_week,
  enroll_number, elc_number, review_count, review_avg, main_teacher_id,
  department_id, semester_id, campus_id
)
SELECT
  COALESCE(cd.courseCode, c.code) as course_code,
  COALESCE(cd.courseName, c.name) as course_name,
  COALESCE(cd.credit, c.credit) as credit,
  cd.period,
  cd.weekHour,
  cd.startWeek,
  cd.endWeek,
  cd.number,
  cd.elcNumber,
  c.review_count,
  c.review_avg,
  ut.id as main_teacher_id,
  ud.id as department_id,
  us.id as semester_id,
  uc.id as campus_id
FROM coursedetail cd
FULL OUTER JOIN jcourse_api_course c ON cd.courseCode = c.code
LEFT JOIN unified_teacher ut ON ut.teacher_name = COALESCE(cd.main_teacher_name, c.main_teacher_name)
LEFT JOIN unified_department ud ON ud.name = COALESCE(cd.faculty, c.department_name)
LEFT JOIN unified_semester us ON us.calendar_id = cd.calendarId OR us.name = c.semester_name
LEFT JOIN unified_campus uc ON uc.code = cd.campus;
```

## 业务逻辑整合

### 1. 选课功能增强

- **选课历史追踪**: 保留原有的选课记录，支持按学期查询
- **选课推荐**: 基于课程评价数据提供选课建议
- **冲突检测**: 整合时间表数据，提供选课冲突提醒

### 2. 评价系统优化

- **评价权限控制**: 只有选过课的学生才能评价
- **评价质量提升**: 结合选课数据验证评价真实性
- **统计分析**: 提供更丰富的课程评价统计报告

### 3. 搜索功能统一

```sql
-- 创建全文搜索视图
CREATE VIEW course_search_view AS
SELECT
  uc.id,
  uc.course_code,
  uc.course_name,
  ut.teacher_name,
  ud.name as department_name,
  GROUP_CONCAT(ucc.name) as categories,
  uc.review_avg,
  uc.review_count,
  CONCAT(uc.course_code, ' ', uc.course_name, ' ', ut.teacher_name) as search_text
FROM unified_course uc
LEFT JOIN unified_teacher ut ON uc.main_teacher_id = ut.id
LEFT JOIN unified_department ud ON uc.department_id = ud.id
LEFT JOIN course_category_relation ccr ON uc.id = ccr.course_id
LEFT JOIN unified_course_category ucc ON ccr.category_id = ucc.id
GROUP BY uc.id;
```

## API接口设计建议

### 1. 统一课程接口

```
GET /api/courses/                    # 获取课程列表
GET /api/courses/{id}/               # 获取课程详情
GET /api/courses/search/             # 课程搜索
GET /api/courses/{id}/reviews/       # 获取课程评价
GET /api/courses/{id}/schedule/      # 获取课程安排
```

### 2. 选课模拟接口

```
GET /api/enrollment/simulation/      # 选课模拟
POST /api/enrollment/validate/       # 选课冲突检测
GET /api/enrollment/recommendations/ # 选课推荐
```

### 3. 评价系统接口

```
GET /api/reviews/                    # 获取评价列表
POST /api/reviews/                   # 创建评价
PUT /api/reviews/{id}/               # 更新评价
DELETE /api/reviews/{id}/            # 删除评价
POST /api/reviews/{id}/react/        # 评价反馈
```

## 性能优化建议

### 1. 索引策略

- 为常用查询字段建立复合索引
- 使用全文搜索索引提升搜索性能
- 对评价统计字段建立索引

### 2. 缓存策略

- 缓存热门课程信息
- 缓存评价统计结果
- 缓存搜索结果

### 3. 数据分区

- 按学期对历史数据进行分区
- 对大表进行水平分区优化查询性能

## 部署考虑

### 1. 数据同步

- 建立ETL流程定期同步选课系统数据
- 实现增量同步机制减少数据传输量
- 建立数据质量监控机制

### 2. 系统集成

- 提供标准化API接口供其他系统调用
- 支持多种认证方式（JAccount、LDAP等）
- 实现统一的日志和监控体系

### 3. 扩展性设计

- 预留字段支持未来功能扩展
- 设计插件化架构支持定制开发
- 支持多租户架构适应不同院系需求

## 总结

本整合方案通过统一数据模型，将选课模拟系统和课程评价系统有机结合，不仅保持了两个系统的核心功能，还通过数据整合提供了更加丰富的功能和更好的用户体验。整合后的系统将为同济大学提供一个完整、高效的课程信息管理和评价平台。