#!/usr/bin/env python3
"""
完整的数据同步脚本
集成镜像站数据同步和数据库同步功能
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from sync_mirror_site import MirrorSiteSyncer, SyncConfig
from static_site_generator import StaticSiteGenerator
from database_sync import TongjiDatabaseSyncer, DatabaseConfig


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="tongji.icu 完整数据同步")

    # 镜像站同步参数
    parser.add_argument("--cookie", help="Cookie字符串")
    parser.add_argument("--output-dir", default="docs", help="输出目录")
    parser.add_argument("--max-pages", type=int, help="每个端点最大页数（用于测试）")
    parser.add_argument("--force-full", action="store_true", help="强制完整同步")
    parser.add_argument("--no-incremental", action="store_true", help="禁用增量更新")
    parser.add_argument("--parallel-workers", type=int, default=4, help="并行工作线程数")

    # 数据库同步参数
    parser.add_argument("--db-host", default="localhost", help="数据库主机")
    parser.add_argument("--db-port", type=int, default=3306, help="数据库端口")
    parser.add_argument("--db-user", default="root", help="数据库用户名")
    parser.add_argument("--db-password", help="数据库密码")
    parser.add_argument("--db-name", default="tongji_course", help="数据库名")

    # 执行控制参数
    parser.add_argument("--mirror-only", action="store_true", help="仅同步镜像站，不同步数据库")
    parser.add_argument("--db-only", action="store_true", help="仅同步数据库，不同步镜像站")
    parser.add_argument("--no-static-gen", action="store_true", help="不生成静态页面")

    # 日志参数
    parser.add_argument("--log-level", default="INFO", help="日志级别")

    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # 输出目录
    output_dir = Path(args.output_dir)
    data_dir = output_dir / "data"

    overall_success = True

    # 阶段1: 镜像站数据同步
    if not args.db_only:
        logger.info("="*60)
        logger.info("阶段1: 镜像站数据同步")
        logger.info("="*60)

        # 配置
        config = SyncConfig(
            output_dir=output_dir,
            data_dir=data_dir,
            max_pages_per_endpoint=args.max_pages,
            force_full_sync=args.force_full,
            incremental_update=not args.no_incremental,
            parallel_workers=args.parallel_workers
        )

        # Cookie
        cookie_string = args.cookie
        if not cookie_string and Path("cookies.ini").exists():
            with open("cookies.ini", "r", encoding="utf-8") as f:
                lines = f.readlines()
            cookie_string = "; ".join(line.strip() for line in lines)

        if not cookie_string:
            logger.warning("未提供Cookie，可能影响数据获取")

        # 运行镜像站同步
        syncer = MirrorSiteSyncer(config, cookie_string)
        mirror_success = syncer.run_sync()

        if not mirror_success:
            logger.error("镜像站数据同步失败")
            overall_success = False
        else:
            logger.info("镜像站数据同步成功")

        # 生成静态页面
        if not args.no_static_gen and mirror_success:
            logger.info("-"*40)
            logger.info("生成静态页面...")
            logger.info("-"*40)

            generator = StaticSiteGenerator(data_dir, output_dir)
            static_success = generator.generate_all_pages()

            if not static_success:
                logger.error("静态页面生成失败")
                overall_success = False
            else:
                logger.info("静态页面生成成功")

    # 阶段2: 数据库同步
    if not args.mirror_only:
        logger.info("="*60)
        logger.info("阶段2: 数据库同步")
        logger.info("="*60)

        # 检查数据文件是否存在
        if not data_dir.exists():
            logger.error(f"数据目录不存在: {data_dir}")
            logger.error("请先运行镜像站同步以生成数据文件")
            overall_success = False
        else:
            # 数据库配置
            db_password = args.db_password or os.getenv('DB_PASSWORD', '')

            if not db_password:
                logger.warning("未提供数据库密码，将尝试无密码连接")

            db_config = DatabaseConfig(
                host=args.db_host,
                port=args.db_port,
                user=args.db_user,
                password=db_password,
                database=args.db_name
            )

            # 运行数据库同步
            db_syncer = TongjiDatabaseSyncer(db_config, data_dir)
            db_success = db_syncer.run_full_sync()

            if not db_success:
                logger.error("数据库同步失败")
                overall_success = False
            else:
                logger.info("数据库同步成功")

    # 输出最终结果
    logger.info("="*60)
    if overall_success:
        logger.info("✅ 完整数据同步成功！")

        if not args.db_only:
            logger.info(f"📁 镜像站输出目录: {output_dir.absolute()}")
            logger.info("🌐 启动本地服务器命令:")
            logger.info(f"   cd {output_dir} && python -m http.server 8000")
            logger.info("   然后访问 http://localhost:8000")

        if not args.mirror_only:
            logger.info(f"💾 数据库: {args.db_host}:{args.db_port}/{args.db_name}")
            logger.info("📊 课程评价数据已同步到数据库")

    else:
        logger.error("❌ 数据同步过程中出现错误，请查看日志了解详情")

    logger.info("="*60)

    # 创建或更新环境配置文件示例
    if not Path(".env.example").exists():
        logger.info("创建环境配置文件示例...")
        with open(".env.example", "w", encoding="utf-8") as f:
            f.write("""# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=tongji_course

# API配置（可选）
TONGJI_ICU_COOKIE=your_cookie_here
""")
        logger.info("已创建 .env.example 文件，请复制为 .env 并配置相应参数")

    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()