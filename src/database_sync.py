#!/usr/bin/env python3
"""
数据库同步脚本
将1.tongji.icu的课程和评价数据同步到选课模拟系统数据库
"""

import os
import sys
import json
import logging
import pymysql
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from sync_mirror_site import MirrorSiteSyncer, SyncConfig


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "tongji_course"
    charset: str = "utf8mb4"


class DatabaseSyncError(Exception):
    """数据库同步异常"""
    pass


class TongjiDatabaseSyncer:
    """同济课程数据库同步器"""

    def __init__(self, db_config: DatabaseConfig, data_dir: Path):
        self.db_config = db_config
        self.data_dir = data_dir
        self.logger = logging.getLogger(__name__)
        self.connection = None

        # 统计信息
        self.stats = {
            "total_courses": 0,
            "total_reviews": 0,
            "matched_courses": 0,
            "new_reviews": 0,
            "updated_reviews": 0,
            "failed_operations": 0,
            "course_mappings": 0
        }

    def connect_database(self) -> bool:
        """连接数据库"""
        try:
            self.connection = pymysql.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                user=self.db_config.user,
                password=self.db_config.password,
                database=self.db_config.database,
                charset=self.db_config.charset,
                autocommit=False
            )
            self.logger.info(f"成功连接到数据库: {self.db_config.host}:{self.db_config.port}/{self.db_config.database}")
            return True
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            return False

    def close_database(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("数据库连接已关闭")

    def execute_sql_file(self, sql_file_path: Path) -> bool:
        """执行SQL文件"""
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # 分割SQL语句（简单方式，根据分号分割）
            sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

            with self.connection.cursor() as cursor:
                for sql in sql_statements:
                    if sql.upper().startswith(('CREATE', 'ALTER', 'INSERT', 'UPDATE')):
                        try:
                            cursor.execute(sql)
                            self.logger.debug(f"执行SQL: {sql[:100]}...")
                        except pymysql.err.OperationalError as e:
                            if "already exists" in str(e) or "Duplicate" in str(e):
                                self.logger.debug(f"表或索引已存在，跳过: {sql[:50]}...")
                                continue
                            else:
                                raise

                self.connection.commit()
                self.logger.info(f"成功执行SQL文件: {sql_file_path}")
                return True

        except Exception as e:
            self.logger.error(f"执行SQL文件失败 {sql_file_path}: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def parse_course_code(self, code: str) -> Tuple[str, Optional[str]]:
        """
        解析课程代码，分离基础课程代码和教学班号
        例如: "00200902" -> ("002009", "02")
        """
        # 去除非数字字符
        clean_code = re.sub(r'[^0-9]', '', code)

        if len(clean_code) >= 6:
            # 假设最后两位是教学班号
            base_code = clean_code[:-2]
            class_number = clean_code[-2:]
            return base_code, class_number
        else:
            return clean_code, None

    def find_matching_course(self, tongji_course: Dict) -> Optional[Dict]:
        """
        在现有数据库中查找匹配的课程
        """
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                # 解析课程代码
                base_code, class_number = self.parse_course_code(tongji_course['code'])

                # 多种匹配策略
                match_queries = [
                    # 1. 精确匹配课程代码
                    "SELECT * FROM coursedetail WHERE code = %s OR courseCode = %s",
                    # 2. 匹配基础课程代码
                    "SELECT * FROM coursedetail WHERE code LIKE %s OR courseCode LIKE %s",
                    # 3. 匹配课程名称
                    "SELECT * FROM coursedetail WHERE name = %s OR courseName = %s"
                ]

                match_params = [
                    (tongji_course['code'], tongji_course['code']),
                    (f"{base_code}%", f"{base_code}%"),
                    (tongji_course['name'], tongji_course['name'])
                ]

                for query, params in zip(match_queries, match_params):
                    cursor.execute(query, params)
                    results = cursor.fetchall()

                    if results:
                        # 返回第一个匹配结果
                        best_match = results[0]

                        # 计算匹配置信度
                        confidence = "LOW"
                        match_method = "code_match"

                        if best_match['code'] == tongji_course['code'] or best_match['courseCode'] == tongji_course['code']:
                            confidence = "HIGH"
                            match_method = "exact_code"
                        elif best_match['name'] == tongji_course['name'] or best_match['courseName'] == tongji_course['name']:
                            confidence = "MEDIUM"
                            match_method = "name_match"

                        return {
                            'course': best_match,
                            'confidence': confidence,
                            'match_method': match_method,
                            'base_code': base_code,
                            'class_number': class_number
                        }

                return None

        except Exception as e:
            self.logger.error(f"查找匹配课程失败: {e}")
            return None

    def save_course_mapping(self, tongji_course: Dict, match_result: Optional[Dict]) -> bool:
        """保存课程映射关系"""
        try:
            with self.connection.cursor() as cursor:
                if match_result:
                    # 有匹配结果
                    course = match_result['course']
                    sql = """
                    INSERT INTO course_mapping
                    (tongji_icu_code, system_course_id, system_course_code, base_course_code,
                     class_number, match_confidence, match_method, is_verified, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    system_course_id = VALUES(system_course_id),
                    system_course_code = VALUES(system_course_code),
                    base_course_code = VALUES(base_course_code),
                    class_number = VALUES(class_number),
                    match_confidence = VALUES(match_confidence),
                    match_method = VALUES(match_method),
                    updated_at = CURRENT_TIMESTAMP
                    """

                    params = (
                        tongji_course['code'],
                        course['id'],
                        course.get('code') or course.get('courseCode'),
                        match_result['base_code'],
                        match_result['class_number'],
                        match_result['confidence'],
                        match_result['match_method'],
                        False,  # 需要人工验证
                        f"自动匹配: {tongji_course['name']} -> {course.get('name') or course.get('courseName')}"
                    )
                else:
                    # 无匹配结果
                    base_code, class_number = self.parse_course_code(tongji_course['code'])
                    sql = """
                    INSERT INTO course_mapping
                    (tongji_icu_code, base_course_code, class_number, match_confidence,
                     match_method, is_verified, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    match_confidence = VALUES(match_confidence),
                    match_method = VALUES(match_method),
                    updated_at = CURRENT_TIMESTAMP
                    """

                    params = (
                        tongji_course['code'],
                        base_code,
                        class_number,
                        'LOW',
                        'no_match',
                        False,
                        f"未找到匹配课程: {tongji_course['name']}"
                    )

                cursor.execute(sql, params)
                return True

        except Exception as e:
            self.logger.error(f"保存课程映射失败: {e}")
            return False

    def save_course_review(self, review: Dict, course_code: str) -> bool:
        """保存课程评价"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO course_review
                (tongji_icu_id, course_code, course_name, teacher_name, department,
                 categories, credit, rating, comment, score, moderator_remark,
                 semester, created_at, modified_at, sync_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                rating = VALUES(rating),
                comment = VALUES(comment),
                score = VALUES(score),
                moderator_remark = VALUES(moderator_remark),
                modified_at = VALUES(modified_at),
                sync_time = VALUES(sync_time)
                """

                # 处理时间格式
                created_at = None
                modified_at = None

                if review.get('created_at'):
                    try:
                        created_at = datetime.strptime(review['created_at'], '%Y/%m/%d %H:%M')
                    except:
                        pass

                if review.get('modified_at'):
                    try:
                        modified_at = datetime.strptime(review['modified_at'], '%Y/%m/%d %H:%M')
                    except:
                        pass

                course_info = review.get('course', {})

                params = (
                    review['id'],
                    course_code,
                    course_info.get('name'),
                    course_info.get('teacher'),
                    None,  # department从course_info中获取
                    None,  # categories
                    None,  # credit
                    review.get('rating'),
                    review.get('comment'),
                    review.get('score'),
                    review.get('moderator_remark'),
                    review.get('semester'),
                    created_at,
                    modified_at,
                    datetime.now()
                )

                cursor.execute(sql, params)
                return True

        except Exception as e:
            self.logger.error(f"保存课程评价失败: {e}")
            return False

    def update_course_review_summary(self, course_code: str, teacher_name: str) -> bool:
        """更新课程评价汇总"""
        try:
            with self.connection.cursor() as cursor:
                # 计算统计信息
                sql_stats = """
                SELECT
                    COUNT(*) as total_reviews,
                    AVG(rating) as avg_rating,
                    MAX(created_at) as last_review_time,
                    JSON_OBJECT(
                        '1', SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END),
                        '2', SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END),
                        '3', SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END),
                        '4', SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END),
                        '5', SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END)
                    ) as rating_distribution
                FROM course_review
                WHERE course_code = %s AND teacher_name = %s AND is_active = TRUE
                """

                cursor.execute(sql_stats, (course_code, teacher_name))
                stats = cursor.fetchone()

                if stats and stats[0] > 0:  # total_reviews > 0
                    # 更新汇总表
                    sql_update = """
                    INSERT INTO course_review_summary
                    (course_code, teacher_name, total_reviews, avg_rating,
                     rating_distribution, last_review_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    total_reviews = VALUES(total_reviews),
                    avg_rating = VALUES(avg_rating),
                    rating_distribution = VALUES(rating_distribution),
                    last_review_time = VALUES(last_review_time),
                    sync_time = CURRENT_TIMESTAMP
                    """

                    cursor.execute(sql_update, stats + (course_code, teacher_name))
                    return True

                return False

        except Exception as e:
            self.logger.error(f"更新课程评价汇总失败: {e}")
            return False

    def update_coursedetail_review_fields(self, course_code: str) -> bool:
        """更新coursedetail表的评价相关字段"""
        try:
            with self.connection.cursor() as cursor:
                # 获取匹配的课程ID
                sql_find = """
                SELECT system_course_id FROM course_mapping
                WHERE tongji_icu_code = %s AND system_course_id IS NOT NULL
                """
                cursor.execute(sql_find, (course_code,))
                result = cursor.fetchone()

                if result:
                    course_id = result[0]

                    # 计算该课程的评价统计
                    sql_stats = """
                    SELECT
                        COUNT(*) as review_count,
                        AVG(rating) as avg_rating
                    FROM course_review
                    WHERE course_code = %s AND is_active = TRUE
                    """
                    cursor.execute(sql_stats, (course_code,))
                    stats = cursor.fetchone()

                    if stats:
                        # 更新coursedetail表
                        sql_update = """
                        UPDATE coursedetail
                        SET has_reviews = %s, review_count = %s, avg_rating = %s,
                            last_review_sync = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """

                        has_reviews = stats[0] > 0
                        cursor.execute(sql_update, (has_reviews, stats[0], stats[1], course_id))
                        return True

                return False

        except Exception as e:
            self.logger.error(f"更新课程详情评价字段失败: {e}")
            return False

    def start_sync_log(self, sync_type: str = "FULL") -> int:
        """开始同步日志"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO sync_log (sync_type, start_time, status)
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (sync_type, datetime.now(), 'RUNNING'))
                self.connection.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"创建同步日志失败: {e}")
            return 0

    def end_sync_log(self, log_id: int, status: str, error_message: str = None):
        """结束同步日志"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                UPDATE sync_log
                SET end_time = %s, status = %s, total_records = %s,
                    new_records = %s, updated_records = %s, failed_records = %s,
                    error_message = %s, sync_details = %s
                WHERE id = %s
                """

                sync_details = json.dumps(self.stats, ensure_ascii=False)

                cursor.execute(sql, (
                    datetime.now(), status,
                    self.stats['total_courses'] + self.stats['total_reviews'],
                    self.stats['new_reviews'], self.stats['updated_reviews'],
                    self.stats['failed_operations'], error_message, sync_details, log_id
                ))
                self.connection.commit()
        except Exception as e:
            self.logger.error(f"更新同步日志失败: {e}")

    def sync_courses_from_data(self) -> bool:
        """从数据文件同步课程信息"""
        courses_file = self.data_dir / "courses.json"

        if not courses_file.exists():
            self.logger.error(f"课程数据文件不存在: {courses_file}")
            return False

        try:
            with open(courses_file, 'r', encoding='utf-8') as f:
                courses_data = json.load(f)

            courses = courses_data.get('courses', [])
            self.stats['total_courses'] = len(courses)

            self.logger.info(f"开始同步 {len(courses)} 门课程")

            for i, course in enumerate(courses, 1):
                if i % 100 == 0:
                    self.logger.info(f"已处理课程: {i}/{len(courses)}")

                try:
                    # 查找匹配课程
                    match_result = self.find_matching_course(course)

                    # 保存映射关系
                    if self.save_course_mapping(course, match_result):
                        self.stats['course_mappings'] += 1

                        if match_result:
                            self.stats['matched_courses'] += 1

                    # 提交批次事务
                    if i % 50 == 0:
                        self.connection.commit()

                except Exception as e:
                    self.logger.error(f"处理课程失败 {course.get('code', 'unknown')}: {e}")
                    self.stats['failed_operations'] += 1

            self.connection.commit()
            self.logger.info(f"课程同步完成，匹配 {self.stats['matched_courses']}/{self.stats['total_courses']} 门课程")
            return True

        except Exception as e:
            self.logger.error(f"同步课程数据失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def sync_reviews_from_data(self) -> bool:
        """从数据文件同步评价信息"""
        reviews_file = self.data_dir / "reviews.json"

        if not reviews_file.exists():
            self.logger.error(f"评价数据文件不存在: {reviews_file}")
            return False

        try:
            with open(reviews_file, 'r', encoding='utf-8') as f:
                reviews_data = json.load(f)

            reviews = reviews_data.get('reviews', [])
            self.stats['total_reviews'] = len(reviews)

            self.logger.info(f"开始同步 {len(reviews)} 条评价")

            # 按课程代码分组
            reviews_by_course = {}
            for review in reviews:
                course_code = review.get('course', {}).get('code')
                if course_code:
                    if course_code not in reviews_by_course:
                        reviews_by_course[course_code] = []
                    reviews_by_course[course_code].append(review)

            for course_code, course_reviews in reviews_by_course.items():
                try:
                    self.logger.debug(f"处理课程 {course_code} 的 {len(course_reviews)} 条评价")

                    for review in course_reviews:
                        if self.save_course_review(review, course_code):
                            self.stats['new_reviews'] += 1
                        else:
                            self.stats['failed_operations'] += 1

                    # 更新评价汇总
                    teacher_names = set(r.get('course', {}).get('teacher') for r in course_reviews if r.get('course', {}).get('teacher'))
                    for teacher_name in teacher_names:
                        self.update_course_review_summary(course_code, teacher_name)

                    # 更新课程详情
                    self.update_coursedetail_review_fields(course_code)

                except Exception as e:
                    self.logger.error(f"处理课程评价失败 {course_code}: {e}")
                    self.stats['failed_operations'] += len(course_reviews)

            self.connection.commit()
            self.logger.info(f"评价同步完成，成功 {self.stats['new_reviews']} 条，失败 {self.stats['failed_operations']} 条")
            return True

        except Exception as e:
            self.logger.error(f"同步评价数据失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def run_full_sync(self) -> bool:
        """运行完整同步"""
        self.logger.info("开始数据库完整同步")

        # 连接数据库
        if not self.connect_database():
            return False

        # 开始同步日志
        log_id = self.start_sync_log("FULL")
        status = "FAILED"
        error_message = None

        try:
            # 1. 执行数据库结构更新
            sql_file = Path(__file__).parent / "database_integration.sql"
            if sql_file.exists():
                self.logger.info("执行数据库结构更新...")
                if not self.execute_sql_file(sql_file):
                    raise DatabaseSyncError("数据库结构更新失败")

            # 2. 同步课程数据
            self.logger.info("同步课程数据...")
            if not self.sync_courses_from_data():
                raise DatabaseSyncError("课程数据同步失败")

            # 3. 同步评价数据
            self.logger.info("同步评价数据...")
            if not self.sync_reviews_from_data():
                raise DatabaseSyncError("评价数据同步失败")

            status = "SUCCESS"
            self.logger.info("数据库同步完成！")
            self.logger.info(f"统计信息: {self.stats}")

        except Exception as e:
            error_message = str(e)
            self.logger.error(f"数据库同步失败: {e}")
            if self.connection:
                self.connection.rollback()

        finally:
            # 结束同步日志
            if log_id:
                self.end_sync_log(log_id, status, error_message)

            # 关闭数据库连接
            self.close_database()

        return status == "SUCCESS"


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="同济课程数据库同步")
    parser.add_argument("--host", default="localhost", help="数据库主机")
    parser.add_argument("--port", type=int, default=3306, help="数据库端口")
    parser.add_argument("--user", default="root", help="数据库用户名")
    parser.add_argument("--password", help="数据库密码")
    parser.add_argument("--database", default="tongji_course", help="数据库名")
    parser.add_argument("--data-dir", default="docs/data", help="数据目录")
    parser.add_argument("--log-level", default="INFO", help="日志级别")

    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )

    # 从环境变量获取数据库密码（如果没有从命令行提供）
    password = args.password or os.getenv('DB_PASSWORD', '')

    # 数据库配置
    db_config = DatabaseConfig(
        host=args.host,
        port=args.port,
        user=args.user,
        password=password,
        database=args.database
    )

    # 数据目录
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"错误: 数据目录不存在: {data_dir}")
        sys.exit(1)

    # 运行同步
    syncer = TongjiDatabaseSyncer(db_config, data_dir)
    success = syncer.run_full_sync()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()