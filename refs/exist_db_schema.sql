CREATE DATABASE IF NOT EXISTS tongji_course;
USE tongji_course;

-- 课程性质表
CREATE TABLE `coursenature` (
  `courseLabelId` INT NOT NULL,
  `courseLabelName` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`courseLabelId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 校区表
CREATE TABLE `campus` (
  `campus` VARCHAR(255) NOT NULL,
  `campusI18n` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`campus`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 学院表
CREATE TABLE `faculty` (
  `faculty` VARCHAR(255) NOT NULL,
  `facultyI18n` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`faculty`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 学期表
CREATE TABLE `calendar` (
  `calendarId` INT NOT NULL,
  `calendarIdI18n` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`calendarId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 授课语言表
CREATE TABLE `language` (
  `teachingLanguage` VARCHAR(255) NOT NULL,
  `teachingLanguageI18n` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`teachingLanguage`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 考核方式表
CREATE TABLE `assessment` (
  `assessmentMode` VARCHAR(255) NOT NULL,
  `assessmentModeI18n` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`assessmentMode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 专业表
CREATE TABLE `major` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(255) DEFAULT NULL,
  `grade` INT DEFAULT NULL,
  `name` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 课程详情表
CREATE TABLE `coursedetail` (
  `id` BIGINT NOT NULL,
  `code` VARCHAR(255) DEFAULT NULL,
  `name` VARCHAR(255) DEFAULT NULL,
  `courseLabelId` INT DEFAULT NULL,
  `assessmentMode` VARCHAR(255) DEFAULT NULL,
  `period` INT DEFAULT NULL,
  `weekHour` INT DEFAULT NULL,
  `campus` VARCHAR(255) DEFAULT NULL,
  `number` INT DEFAULT NULL,
  `elcNumber` INT DEFAULT NULL,
  `startWeek` INT DEFAULT NULL,
  `endWeek` INT DEFAULT NULL,
  `courseCode` VARCHAR(255) DEFAULT NULL,
  `courseName` VARCHAR(255) DEFAULT NULL,
  `credit` DOUBLE DEFAULT NULL,
  `teachingLanguage` VARCHAR(255) DEFAULT NULL,
  `faculty` VARCHAR(255) DEFAULT NULL,
  `calendarId` INT DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `courseCode` (`courseCode`),
  KEY `nature_idx` (`courseLabelId`),  
  KEY `assess_idx` (`assessmentMode`),  
  KEY `campusKey_idx` (`campus`),  
  KEY `facultyKey_idx` (`faculty`),  
  KEY `calendarKey_idx` (`calendarId`),  
  KEY `langKey_idx` (`teachingLanguage`),  

  CONSTRAINT `coursedetail_ibfk_1` FOREIGN KEY (`courseLabelId`) REFERENCES `coursenature` (`courseLabelId`),
  CONSTRAINT `coursedetail_ibfk_2` FOREIGN KEY (`campus`) REFERENCES `campus` (`campus`),
  CONSTRAINT `coursedetail_ibfk_3` FOREIGN KEY (`faculty`) REFERENCES `faculty` (`faculty`),
  CONSTRAINT `coursedetail_ibfk_4` FOREIGN KEY (`calendarId`) REFERENCES `calendar` (`calendarId`),
  CONSTRAINT `coursedetail_ibfk_5` FOREIGN KEY (`teachingLanguage`) REFERENCES `language` (`teachingLanguage`),
  CONSTRAINT `coursedetail_ibfk_6` FOREIGN KEY (`assessmentMode`) REFERENCES `assessment` (`assessmentMode`),

  CONSTRAINT `natureKey` FOREIGN KEY (`courseLabelId`) REFERENCES `coursenature` (`courseLabelId`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `campusKey` FOREIGN KEY (`campus`) REFERENCES `campus` (`campus`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `facultyKey` FOREIGN KEY (`faculty`) REFERENCES `faculty` (`faculty`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `calendarKey` FOREIGN KEY (`calendarId`) REFERENCES `calendar` (`calendarId`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `langKey` FOREIGN KEY (`teachingLanguage`) REFERENCES `language` (`teachingLanguage`),
  CONSTRAINT `assessKey` FOREIGN KEY (`assessmentMode`) REFERENCES `assessment` (`assessmentMode`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 教师表
CREATE TABLE `teacher` (
  `id` BIGINT NOT NULL,
  `teachingClassId` BIGINT DEFAULT NULL,
  `teacherCode` VARCHAR(255) DEFAULT NULL,
  `teacherName` VARCHAR(255) DEFAULT NULL,
  `arrangeInfoText` MEDIUMTEXT DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `teachingClassId` (`teachingClassId`),
  CONSTRAINT `teacher_ibfk_1` FOREIGN KEY (`teachingClassId`) REFERENCES `coursedetail` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 专业与课程关联表
CREATE TABLE `majorandcourse` (
  `id` INT NOT NULL AUTO_INCREMENT,  
  `majorId` INT NOT NULL,
  `courseId` BIGINT NOT NULL,
  PRIMARY KEY (`id`),  
    KEY `courseKey_idx` (`courseId`),  
    KEY `majorKeyForMajor_idx` (`majorId`),  
    CONSTRAINT `courseKeyForMajor` FOREIGN KEY (`courseId`) REFERENCES `coursedetail` (`id`),  
    CONSTRAINT `majorKeyForMajor` FOREIGN KEY (`majorId`) REFERENCES `major` (`id`),
  CONSTRAINT `majorandcourse_ibfk_1` FOREIGN KEY (`majorId`) REFERENCES `major` (`id`),
  CONSTRAINT `majorandcourse_ibfk_2` FOREIGN KEY (`courseId`) REFERENCES `coursedetail` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 抓取日志表
CREATE TABLE `fetchlog` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `fetchTime` DATETIME DEFAULT NULL,
  `msg` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;