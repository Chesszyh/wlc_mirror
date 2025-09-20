-- ===============================================
-- 同济大学课程评价系统数据库集成方案
-- 基于现有选课模拟系统数据库添加课程评价功能
-- ===============================================

USE tongji_course;

-- 课程评价表 - 存储来自1.tongji.icu的课程评价
CREATE TABLE `course_review` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `tongji_icu_id` BIGINT NOT NULL COMMENT '1.tongji.icu系统中的原始ID',
  `course_code` VARCHAR(255) NOT NULL COMMENT '课程编码，对应coursedetail表的code字段',
  `course_name` VARCHAR(255) DEFAULT NULL COMMENT '课程名称',
  `teacher_name` VARCHAR(255) DEFAULT NULL COMMENT '教师姓名',
  `department` VARCHAR(255) DEFAULT NULL COMMENT '开课院系',
  `categories` JSON DEFAULT NULL COMMENT '课程分类，存储数组',
  `credit` DOUBLE DEFAULT NULL COMMENT '学分',
  `rating` DOUBLE DEFAULT NULL COMMENT '评分(1-5)',
  `rating_count` INT DEFAULT 0 COMMENT '评价数量',
  `rating_avg` DOUBLE DEFAULT NULL COMMENT '平均评分',
  `semester` VARCHAR(255) DEFAULT NULL COMMENT '学期',
  `comment` TEXT DEFAULT NULL COMMENT '评价内容',
  `score` VARCHAR(50) DEFAULT NULL COMMENT '成绩等级',
  `moderator_remark` TEXT DEFAULT NULL COMMENT '管理员备注',
  `created_at` DATETIME DEFAULT NULL COMMENT '创建时间',
  `modified_at` DATETIME DEFAULT NULL COMMENT '修改时间',
  `sync_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '同步时间',
  `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否有效',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_tongji_icu_id` (`tongji_icu_id`),
  KEY `idx_course_code` (`course_code`),
  KEY `idx_teacher_name` (`teacher_name`),
  KEY `idx_department` (`department`),
  KEY `idx_rating` (`rating`),
  KEY `idx_semester` (`semester`),
  KEY `idx_sync_time` (`sync_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='课程评价表';

-- 课程评价汇总表 - 对每门课程的评价进行统计汇总
CREATE TABLE `course_review_summary` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `course_code` VARCHAR(255) NOT NULL COMMENT '课程编码',
  `teacher_name` VARCHAR(255) NOT NULL COMMENT '教师姓名',
  `total_reviews` INT DEFAULT 0 COMMENT '总评价数',
  `avg_rating` DOUBLE DEFAULT NULL COMMENT '平均评分',
  `rating_distribution` JSON DEFAULT NULL COMMENT '评分分布统计',
  `last_review_time` DATETIME DEFAULT NULL COMMENT '最后一次评价时间',
  `sync_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '同步时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_course_teacher` (`course_code`, `teacher_name`),
  KEY `idx_avg_rating` (`avg_rating`),
  KEY `idx_total_reviews` (`total_reviews`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='课程评价汇总表';

-- 课程匹配映射表 - 将1.tongji.icu的课程与现有课程系统进行匹配
CREATE TABLE `course_mapping` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `tongji_icu_code` VARCHAR(255) NOT NULL COMMENT '1.tongji.icu中的课程代码',
  `system_course_id` BIGINT DEFAULT NULL COMMENT '本系统coursedetail表的id',
  `system_course_code` VARCHAR(255) DEFAULT NULL COMMENT '本系统课程代码',
  `base_course_code` VARCHAR(255) DEFAULT NULL COMMENT '基础课程代码(去除教学班号)',
  `class_number` VARCHAR(10) DEFAULT NULL COMMENT '教学班号',
  `match_confidence` ENUM('HIGH', 'MEDIUM', 'LOW', 'MANUAL') DEFAULT 'LOW' COMMENT '匹配置信度',
  `match_method` VARCHAR(100) DEFAULT NULL COMMENT '匹配方法',
  `is_verified` BOOLEAN DEFAULT FALSE COMMENT '是否人工验证',
  `notes` TEXT DEFAULT NULL COMMENT '备注说明',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_tongji_icu_code` (`tongji_icu_code`),
  KEY `idx_system_course_id` (`system_course_id`),
  KEY `idx_base_course_code` (`base_course_code`),
  KEY `idx_match_confidence` (`match_confidence`),
  CONSTRAINT `fk_course_mapping_coursedetail` FOREIGN KEY (`system_course_id`) REFERENCES `coursedetail` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='课程匹配映射表';

-- 数据同步日志表 - 记录同步过程和状态
CREATE TABLE `sync_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `sync_type` ENUM('FULL', 'INCREMENTAL') NOT NULL COMMENT '同步类型',
  `start_time` DATETIME NOT NULL COMMENT '开始时间',
  `end_time` DATETIME DEFAULT NULL COMMENT '结束时间',
  `status` ENUM('RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL') DEFAULT 'RUNNING' COMMENT '同步状态',
  `total_records` INT DEFAULT 0 COMMENT '总记录数',
  `new_records` INT DEFAULT 0 COMMENT '新增记录数',
  `updated_records` INT DEFAULT 0 COMMENT '更新记录数',
  `failed_records` INT DEFAULT 0 COMMENT '失败记录数',
  `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
  `sync_details` JSON DEFAULT NULL COMMENT '同步详情',
  PRIMARY KEY (`id`),
  KEY `idx_sync_type` (`sync_type`),
  KEY `idx_status` (`status`),
  KEY `idx_start_time` (`start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='数据同步日志表';

-- 更新现有coursedetail表，添加评价相关字段
ALTER TABLE `coursedetail`
ADD COLUMN `has_reviews` BOOLEAN DEFAULT FALSE COMMENT '是否有评价数据',
ADD COLUMN `review_count` INT DEFAULT 0 COMMENT '评价数量',
ADD COLUMN `avg_rating` DOUBLE DEFAULT NULL COMMENT '平均评分',
ADD COLUMN `last_review_sync` DATETIME DEFAULT NULL COMMENT '最后同步评价时间',
ADD INDEX `idx_has_reviews` (`has_reviews`),
ADD INDEX `idx_avg_rating` (`avg_rating`);

-- 创建视图：课程详情与评价汇总
CREATE VIEW `v_course_with_reviews` AS
SELECT
    cd.id,
    cd.code,
    cd.name,
    cd.courseCode,
    cd.courseName,
    cd.credit,
    cd.faculty,
    cd.campus,
    cd.calendarId,
    t.teacherName,
    crs.total_reviews,
    crs.avg_rating,
    crs.last_review_time,
    cd.has_reviews
FROM coursedetail cd
LEFT JOIN teacher t ON cd.id = t.teachingClassId
LEFT JOIN course_review_summary crs ON cd.code = crs.course_code AND t.teacherName = crs.teacher_name;

-- 创建索引优化查询性能
CREATE INDEX idx_course_review_code_teacher ON course_review(course_code, teacher_name);
CREATE INDEX idx_course_review_rating_time ON course_review(rating, created_at);
CREATE INDEX idx_course_review_active ON course_review(is_active, sync_time);