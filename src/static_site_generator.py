#!/usr/bin/env python3
"""
镜像站静态页面生成器

根据同步的JSON数据生成HTML页面，配合MkDocs使用。
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader, Template
import sys


class StaticSiteGenerator:
    """静态站点生成器"""

    def __init__(self, data_dir: Path, output_dir: Path):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.pages_dir = self.output_dir / "pages"

        # 设置日志
        self.logger = logging.getLogger(__name__)

        # 确保目录存在
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        (self.pages_dir / "courses").mkdir(exist_ok=True)
        (self.pages_dir / "reviews").mkdir(exist_ok=True)
        (self.pages_dir / "search").mkdir(exist_ok=True)
        (self.pages_dir / "statistics").mkdir(exist_ok=True)

        # 初始化模板环境
        self._init_templates()

    def _init_templates(self):
        """初始化Jinja2模板"""
        # 创建模板目录
        template_dir = self.output_dir / "templates"
        template_dir.mkdir(exist_ok=True)

        # 如果模板不存在，创建默认模板
        self._create_default_templates(template_dir)

        # 初始化Jinja2环境
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )

        # 注册过滤器
        self.jinja_env.filters['datetime_format'] = self._datetime_format
        self.jinja_env.filters['rating_stars'] = self._rating_stars

    def _create_default_templates(self, template_dir: Path):
        """创建默认模板"""

        # 基础模板
        base_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}同济课程评价镜像站{% endblock %}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }
        .course-card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; background: #fff; }
        .course-title { font-size: 1.2em; font-weight: bold; color: #333; margin-bottom: 10px; }
        .course-meta { color: #666; font-size: 0.9em; margin-bottom: 10px; }
        .rating { color: #f39c12; font-weight: bold; }
        .review-card { border-left: 3px solid #3498db; padding: 15px; margin-bottom: 15px; background: #f8f9fa; }
        .review-rating { color: #f39c12; margin-bottom: 8px; }
        .review-content { margin-bottom: 8px; }
        .review-meta { color: #666; font-size: 0.8em; }
        .breadcrumb { margin-bottom: 20px; color: #666; }
        .breadcrumb a { color: #3498db; text-decoration: none; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #3498db; }
        .stat-label { color: #666; }
        .search-box { width: 100%; max-width: 500px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 20px; }
        .filter-section { margin-bottom: 20px; }
        .filter-label { display: inline-block; width: 100px; font-weight: bold; }
        .tag { display: inline-block; background: #e9ecef; padding: 4px 8px; border-radius: 4px; margin: 2px; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><a href="../index.html" style="text-decoration: none; color: inherit;">同济课程评价镜像站</a></h1>
            <nav>
                <a href="../index.html">首页</a> |
                <a href="../pages/courses/index.html">课程列表</a> |
                <a href="../pages/search/index.html">搜索</a> |
                <a href="../pages/statistics/index.html">统计</a>
            </nav>
        </div>

        {% block content %}{% endblock %}

        <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; color: #666; text-align: center;">
            <p>数据来源: <a href="https://1.tongji.icu" target="_blank">1.tongji.icu</a> |
            最后更新: {{ last_updated | datetime_format }}</p>
            <p>本站为镜像站，仅供参考。如需最新信息请访问原站。</p>
        </footer>
    </div>
</body>
</html>'''

        # 首页模板
        index_template = '''{% extends "base.html" %}

{% block title %}同济课程评价镜像站 - 首页{% endblock %}

{% block content %}
<div class="breadcrumb">
    首页
</div>

<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-number">{{ stats.total_courses or 0 }}</div>
        <div class="stat-label">总课程数</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{{ stats.total_reviews or 0 }}</div>
        <div class="stat-label">总评价数</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{{ stats.departments_count or 0 }}</div>
        <div class="stat-label">院系数</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{{ stats.categories_count or 0 }}</div>
        <div class="stat-label">课程类别数</div>
    </div>
</div>

<h2>功能导航</h2>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
    <div class="course-card">
        <h3><a href="pages/courses/index.html">课程列表</a></h3>
        <p>浏览所有课程，支持按院系和类别筛选</p>
    </div>
    <div class="course-card">
        <h3><a href="pages/search/index.html">课程搜索</a></h3>
        <p>搜索课程名、课程代码、教师姓名</p>
    </div>
    <div class="course-card">
        <h3><a href="pages/statistics/index.html">数据统计</a></h3>
        <p>查看课程和评价的统计信息</p>
    </div>
</div>

{% if recent_reviews %}
<h2>最新评价</h2>
{% for review in recent_reviews[:5] %}
<div class="review-card">
    <div class="review-rating">{{ review.rating | rating_stars }}</div>
    <div class="review-content">{{ review.comment[:100] }}{% if review.comment|length > 100 %}...{% endif %}</div>
    <div class="review-meta">
        课程: {{ review.course.code }} {{ review.course.name }} |
        学期: {{ review.semester }} |
        时间: {{ review.created_at | datetime_format }}
    </div>
</div>
{% endfor %}
{% endif %}

{% endblock %}'''

        # 课程列表模板
        courses_template = '''{% extends "base.html" %}

{% block title %}课程列表 - 同济课程评价镜像站{% endblock %}

{% block content %}
<div class="breadcrumb">
    <a href="../../index.html">首页</a> > 课程列表
</div>

<h1>课程列表</h1>

<div class="filter-section">
    <p><strong>总计: {{ courses|length }} 门课程</strong></p>
</div>

{% for course in courses %}
<div class="course-card">
    <div class="course-title">
        <a href="details/{{ course.id }}.html">{{ course.code }} {{ course.name }}</a>
    </div>
    <div class="course-meta">
        院系: {{ course.department }} |
        教师: {{ course.teacher or '未知' }} |
        学分: {{ course.credit }}
        {% if course.categories %}
        | 类别: {% for cat in course.categories %}<span class="tag">{{ cat }}</span>{% endfor %}
        {% endif %}
    </div>
    {% if course.rating %}
    <div class="rating">
        评分: {{ course.rating.avg|round(1) }}/5.0 ({{ course.rating.count }} 条评价)
        {{ course.rating.avg | rating_stars }}
    </div>
    {% endif %}
</div>
{% endfor %}

{% endblock %}'''

        # 课程详情模板
        course_detail_template = '''{% extends "base.html" %}

{% block title %}{{ course.code }} {{ course.name }} - 课程详情{% endblock %}

{% block content %}
<div class="breadcrumb">
    <a href="../../../index.html">首页</a> >
    <a href="../index.html">课程列表</a> >
    {{ course.code }} {{ course.name }}
</div>

<h1>{{ course.code }} {{ course.name }}</h1>

<div class="course-card">
    <h2>课程信息</h2>
    <p><strong>课程代码:</strong> {{ course.code }}</p>
    <p><strong>课程名称:</strong> {{ course.name }}</p>
    <p><strong>开课单位:</strong> {{ course.department }}</p>
    <p><strong>学分:</strong> {{ course.credit }}</p>
    {% if course.main_teacher %}
    <p><strong>主讲教师:</strong> {{ course.main_teacher.name }}</p>
    {% endif %}
    {% if course.teacher_group %}
    <p><strong>教师组:</strong>
    {% for teacher in course.teacher_group %}{{ teacher.name }}{% if not loop.last %}, {% endif %}{% endfor %}
    </p>
    {% endif %}
    {% if course.categories %}
    <p><strong>课程类别:</strong>
    {% for cat in course.categories %}<span class="tag">{{ cat }}</span>{% endfor %}
    </p>
    {% endif %}
    {% if course.rating %}
    <p><strong>综合评分:</strong>
        <span class="rating">{{ course.rating.avg|round(1) }}/5.0 {{ course.rating.avg | rating_stars }}</span>
        ({{ course.rating.count }} 条评价)
    </p>
    {% endif %}
</div>

{% if reviews %}
<h2>课程评价 ({{ reviews|length }} 条)</h2>
{% for review in reviews %}
<div class="review-card">
    <div class="review-rating">{{ review.rating | rating_stars }} ({{ review.rating }}/5)</div>
    <div class="review-content">{{ review.comment }}</div>
    <div class="review-meta">
        学期: {{ review.semester }} |
        成绩: {{ review.score or '未填写' }} |
        发布时间: {{ review.created_at | datetime_format }}
        {% if review.reactions %}
        | 👍 {{ review.reactions.approves or 0 }} 👎 {{ review.reactions.disapproves or 0 }}
        {% endif %}
    </div>
</div>
{% endfor %}
{% else %}
<p>暂无评价</p>
{% endif %}

{% endblock %}'''

        # 写入模板文件
        templates = {
            'base.html': base_template,
            'index.html': index_template,
            'courses.html': courses_template,
            'course_detail.html': course_detail_template
        }

        for filename, content in templates.items():
            template_file = template_dir / filename
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(content)

    def _datetime_format(self, value, format='%Y-%m-%d %H:%M'):
        """日期时间格式化过滤器"""
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.strftime(format)
            except:
                return value
        return str(value)

    def _rating_stars(self, rating):
        """评分星星过滤器"""
        if not rating:
            return ''
        try:
            rating = float(rating)
            full_stars = int(rating)
            half_star = 1 if rating - full_stars >= 0.5 else 0
            empty_stars = 5 - full_stars - half_star

            return '★' * full_stars + '☆' * half_star + '☆' * empty_stars
        except:
            return ''

    def _load_json_data(self, file_path: Path) -> Any:
        """加载JSON数据"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"加载 {file_path} 失败: {e}")
        return None

    def generate_index_page(self):
        """生成首页"""
        self.logger.info("生成首页...")

        # 加载数据
        stats_data = self._load_json_data(self.data_dir / "statistics" / "summary.json")
        courses_index = self._load_json_data(self.data_dir / "courses" / "index.json")
        reviews_latest = self._load_json_data(self.data_dir / "reviews" / "latest" / "latest.json")
        departments = self._load_json_data(self.data_dir / "filters" / "departments.json")
        categories = self._load_json_data(self.data_dir / "filters" / "categories.json")

        # 准备统计数据
        stats = {
            'total_courses': courses_index.get('total', 0) if courses_index else 0,
            'total_reviews': stats_data.get('review_count', 0) if stats_data else 0,
            'departments_count': len(departments) if departments else 0,
            'categories_count': len(categories) if categories else 0,
        }

        # 渲染模板
        template = self.jinja_env.get_template('index.html')
        html = template.render(
            stats=stats,
            recent_reviews=reviews_latest.get('reviews', []) if reviews_latest else [],
            last_updated=datetime.now().isoformat()
        )

        # 写入文件
        output_file = self.output_dir / "index.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

    def generate_courses_pages(self):
        """生成课程页面"""
        self.logger.info("生成课程页面...")

        # 加载课程数据
        courses_index = self._load_json_data(self.data_dir / "courses" / "index.json")
        if not courses_index:
            self.logger.error("无法加载课程索引")
            return

        courses = courses_index.get('courses', [])

        # 生成课程列表页
        template = self.jinja_env.get_template('courses.html')
        html = template.render(
            courses=courses,
            last_updated=courses_index.get('last_updated')
        )

        courses_index_file = self.pages_dir / "courses" / "index.html"
        with open(courses_index_file, 'w', encoding='utf-8') as f:
            f.write(html)

        # 生成课程详情页
        details_dir = self.pages_dir / "courses" / "details"
        details_dir.mkdir(exist_ok=True)

        template = self.jinja_env.get_template('course_detail.html')

        for course in courses:
            course_id = course['id']

            # 加载课程详情
            course_detail = self._load_json_data(
                self.data_dir / "courses" / "details" / f"{course_id}.json"
            )

            # 加载课程评价
            course_reviews_data = self._load_json_data(
                self.data_dir / "reviews" / "by-course" / f"{course_id}.json"
            )
            reviews = course_reviews_data.get('reviews', []) if course_reviews_data else []

            # 使用详情数据，如果没有则使用索引数据
            course_data = course_detail or course

            html = template.render(
                course=course_data,
                reviews=reviews,
                last_updated=datetime.now().isoformat()
            )

            detail_file = details_dir / f"{course_id}.html"
            with open(detail_file, 'w', encoding='utf-8') as f:
                f.write(html)

        self.logger.info(f"生成了 {len(courses)} 个课程详情页")

    def generate_search_page(self):
        """生成搜索页面"""
        self.logger.info("生成搜索页面...")

        search_dir = self.pages_dir / "search"
        search_dir.mkdir(exist_ok=True)

        # 简单的搜索页面
        search_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>课程搜索 - 同济课程评价镜像站</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }
        .breadcrumb { margin-bottom: 20px; color: #666; }
        .breadcrumb a { color: #3498db; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><a href="../../index.html" style="text-decoration: none; color: inherit;">同济课程评价镜像站</a></h1>
            <nav>
                <a href="../../index.html">首页</a> |
                <a href="../courses/index.html">课程列表</a> |
                <a href="index.html">搜索</a> |
                <a href="../statistics/index.html">统计</a>
            </nav>
        </div>

        <div class="breadcrumb">
            <a href="../../index.html">首页</a> > 课程搜索
        </div>

        <h1>课程搜索</h1>

        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h2>搜索功能说明</h2>
            <p>由于这是静态镜像站，暂不支持实时搜索功能。</p>
            <p>您可以通过以下方式查找课程：</p>
            <ul>
                <li><a href="../courses/index.html">浏览课程列表</a></li>
                <li>使用浏览器的搜索功能 (Ctrl+F) 在页面中查找</li>
                <li>访问原站 <a href="https://1.tongji.icu" target="_blank">1.tongji.icu</a> 使用完整搜索功能</li>
            </ul>
        </div>

        <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; color: #666; text-align: center;">
            <p>数据来源: <a href="https://1.tongji.icu" target="_blank">1.tongji.icu</a> |
            最后更新: ''' + datetime.now().strftime('%Y-%m-%d %H:%M') + '''</p>
            <p>本站为镜像站，仅供参考。如需最新信息请访问原站。</p>
        </footer>
    </div>
</body>
</html>'''

        search_file = search_dir / "index.html"
        with open(search_file, 'w', encoding='utf-8') as f:
            f.write(search_html)

    def generate_statistics_page(self):
        """生成统计页面"""
        self.logger.info("生成统计页面...")

        stats_dir = self.pages_dir / "statistics"
        stats_dir.mkdir(exist_ok=True)

        # 加载统计数据
        stats_data = self._load_json_data(self.data_dir / "statistics" / "summary.json")
        courses_index = self._load_json_data(self.data_dir / "courses" / "index.json")
        departments = self._load_json_data(self.data_dir / "filters" / "departments.json")
        categories = self._load_json_data(self.data_dir / "filters" / "categories.json")

        # 准备数据
        basic_stats = {
            'total_courses': courses_index.get('total', 0) if courses_index else 0,
            'total_reviews': stats_data.get('review_count', 0) if stats_data else 0,
            'departments_count': len(departments) if departments else 0,
            'categories_count': len(categories) if categories else 0,
        }

        # 生成HTML内容
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据统计 - 同济课程评价镜像站</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .breadcrumb {{ margin-bottom: 20px; color: #666; }}
        .breadcrumb a {{ color: #3498db; text-decoration: none; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .stat-label {{ color: #666; }}
        .tag {{ display: inline-block; background: #e9ecef; padding: 4px 8px; border-radius: 4px; margin: 2px; font-size: 0.8em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><a href="../../index.html" style="text-decoration: none; color: inherit;">同济课程评价镜像站</a></h1>
            <nav>
                <a href="../../index.html">首页</a> |
                <a href="../courses/index.html">课程列表</a> |
                <a href="../search/index.html">搜索</a> |
                <a href="index.html">统计</a>
            </nav>
        </div>

        <div class="breadcrumb">
            <a href="../../index.html">首页</a> > 数据统计
        </div>

        <h1>数据统计</h1>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{basic_stats['total_courses']}</div>
                <div class="stat-label">总课程数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{basic_stats['total_reviews']}</div>
                <div class="stat-label">总评价数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{basic_stats['departments_count']}</div>
                <div class="stat-label">院系数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{basic_stats['categories_count']}</div>
                <div class="stat-label">课程类别数</div>
            </div>
        </div>'''

        # 院系分布
        if departments:
            html += '''
        <h2>院系分布</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 10px;">'''
            for dept in departments[:20]:
                dept_name = dept.get('name', '未知院系') if isinstance(dept, dict) else str(dept)
                course_count = dept.get('course_count', 0) if isinstance(dept, dict) else 0
                html += f'<div class="tag">{dept_name} ({course_count})</div>'
            html += '</div>'

        # 课程类别分布
        if categories:
            html += '''
        <h2>课程类别分布</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">'''
            for cat in categories[:30]:
                cat_name = cat.get('name', '未知类别') if isinstance(cat, dict) else str(cat)
                course_count = cat.get('course_count', 0) if isinstance(cat, dict) else 0
                html += f'<div class="tag">{cat_name} ({course_count})</div>'
            html += '</div>'

        html += f'''
        <h2>数据更新信息</h2>
        <p><strong>最后更新时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p><strong>数据来源:</strong> <a href="https://1.tongji.icu" target="_blank">1.tongji.icu</a></p>

        <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; color: #666; text-align: center;">
            <p>数据来源: <a href="https://1.tongji.icu" target="_blank">1.tongji.icu</a> |
            最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>本站为镜像站，仅供参考。如需最新信息请访问原站。</p>
        </footer>
    </div>
</body>
</html>'''

        stats_file = stats_dir / "index.html"
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write(html)

    def generate_all_pages(self):
        """生成所有页面"""
        self.logger.info("开始生成静态页面...")

        try:
            self.generate_index_page()
            self.generate_courses_pages()
            self.generate_search_page()
            self.generate_statistics_page()

            self.logger.info("静态页面生成完成")
            return True

        except Exception as e:
            self.logger.error(f"生成静态页面失败: {e}")
            return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="生成镜像站静态页面")
    parser.add_argument("--data-dir", default="docs/data", help="数据目录")
    parser.add_argument("--output-dir", default="docs", help="输出目录")

    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    generator = StaticSiteGenerator(args.data_dir, args.output_dir)
    success = generator.generate_all_pages()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()