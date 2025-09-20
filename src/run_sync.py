#!/usr/bin/env python3
"""
镜像站完整同步和生成脚本

集成数据同步和静态页面生成功能。
"""
import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from sync_mirror_site import MirrorSiteSyncer, SyncConfig
from static_site_generator import StaticSiteGenerator


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="tongji.icu 镜像站完整同步")
    parser.add_argument("--cookie", help="Cookie字符串")
    parser.add_argument("--output-dir", default="docs", help="输出目录")
    parser.add_argument("--max-pages", type=int, help="每个端点最大页数（用于测试）")
    parser.add_argument("--force-full", action="store_true", help="强制完整同步")
    parser.add_argument("--no-incremental", action="store_true", help="禁用增量更新")
    parser.add_argument("--parallel-workers", type=int, default=4, help="并行工作线程数")
    parser.add_argument("--sync-only", action="store_true", help="仅同步数据，不生成页面")
    parser.add_argument("--generate-only", action="store_true", help="仅生成页面，不同步数据")

    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # 输出目录
    output_dir = Path(args.output_dir)
    data_dir = output_dir / "data"

    success = True

    # 数据同步
    if not args.generate_only:
        logger.info("="*50)
        logger.info("开始数据同步阶段")
        logger.info("="*50)

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

        # 运行同步
        syncer = MirrorSiteSyncer(config, cookie_string)
        sync_success = syncer.run_sync()

        if not sync_success:
            logger.error("数据同步失败")
            success = False

    # 生成静态页面
    if not args.sync_only and success:
        logger.info("="*50)
        logger.info("开始静态页面生成阶段")
        logger.info("="*50)

        generator = StaticSiteGenerator(data_dir, output_dir)
        generate_success = generator.generate_all_pages()

        if not generate_success:
            logger.error("静态页面生成失败")
            success = False

    if success:
        logger.info("="*50)
        logger.info("镜像站同步完成！")
        logger.info(f"输出目录: {output_dir.absolute()}")
        logger.info("您可以使用以下命令启动本地服务器查看：")
        logger.info(f"cd {output_dir} && python -m http.server 8000")
        logger.info("然后访问 http://localhost:8000")
        logger.info("="*50)
    else:
        logger.error("镜像站同步失败，请查看日志了解详情")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()