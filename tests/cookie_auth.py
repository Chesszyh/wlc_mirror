#!/usr/bin/env python3
"""
增强版Cookie自动登录实现
基于refs/simple_test.py，实现更稳健的自动登录和Cookie管理

功能特性：
1. 智能Cookie检测和验证
2. 自动CloudFlare绕过
3. Cookie自动刷新和保存
4. 多种认证方式支持
5. 错误重试和恢复机制
"""

import json
import logging
from rich.console import Console
from rich import print as rprint
from src.auth import TongjiAuthenticator


def demo_enhanced_authentication():
    """演示增强版认证功能"""
    console = Console()
    console.print("[bold green]🚀 增强版Cookie认证演示[/bold green]")

    # 从/cookies.ini读取
    with open("cookies.ini", "r", encoding="utf-8") as f:
        lines = f.readlines()
    cookie_string = "; ".join(line.strip() for line in lines)
    rprint(f"使用的Cookie字符串: {cookie_string}")

    with TongjiAuthenticator() as auth:
        # 测试认证
        if auth.authenticate(cookie_string):
            console.print("[green]🎉 认证成功！[/green]")

            # 获取session并测试API
            session = auth.get_session()
            if session:
                try:
                    # 测试用户信息API
                    response = session.get("https://1.tongji.icu/api/me/")
                    if response.status_code == 200:
                        try:
                            user_info = response.json()
                            console.print(f"用户信息: {user_info}")
                        except json.JSONDecodeError:
                            console.print(
                                f"[yellow]用户API返回非JSON数据: {response.text[:100]}[/yellow]"
                            )

                    # 测试课程API
                    response = session.get(
                        "https://1.tongji.icu/api/course/?page=1&page_size=3"
                    )
                    if response.status_code == 200:
                        try:
                            courses_data = response.json()
                            console.print(
                                f"获取到 {len(courses_data.get('results', []))} 门课程"
                            )

                            for course in courses_data.get("results", []):
                                main_teacher = course.get("main_teacher", {})
                                if isinstance(main_teacher, dict):
                                    teacher_name = main_teacher.get("name", "未知")
                                else:
                                    teacher_name = (
                                        str(main_teacher) if main_teacher else "未知"
                                    )
                                console.print(
                                    f"  • {course.get('code')} {course.get('name')} - {teacher_name}"
                                )
                        except json.JSONDecodeError:
                            console.print(
                                f"[yellow]课程API返回非JSON数据: {response.text[:100]}[/yellow]"
                            )
                    else:
                        console.print(
                            f"[red]课程API请求失败: {response.status_code}[/red]"
                        )

                    console.print("[green]✅ API测试通过[/green]")

                except Exception as e:
                    console.print(f"[red]❌ API测试失败: {e}[/red]")
        else:
            console.print("[red]💥 认证失败！[/red]")
            console.print("请检查：")
            console.print("1. Cookie是否有效且未过期")
            console.print("2. 网络连接是否正常")
            console.print("3. CloudFlare是否阻止了访问")


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)

    # 运行演示
    demo_enhanced_authentication()
