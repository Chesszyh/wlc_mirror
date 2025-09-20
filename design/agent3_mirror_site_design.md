# 1.tongji.icu 镜像站设计文档

## 1. 项目概述

本文档描述了为 1.tongji.icu 课程评价系统创建镜像站的设计方案。镜像站将使用 GitHub Pages 部署，实现静态站点的自动化数据同步和增量更新。

## 2. 现有系统分析

### 2.1 原站前端结构分析

通过分析 `wlc_frontend` 的代码结构，发现原站具有以下特征：

#### 2.1.1 技术栈
- **框架**: Next.js (React)
- **UI组件**: Ant Design
- **样式**: CSS + Ant Design定制主题
- **数据获取**: API调用 + SWR缓存

#### 2.1.2 页面结构
- **课程详情页** (`/course/[id].tsx`): 展示课程基本信息、评价列表、相关课程
- **课程列表页** (`/courses.tsx`): 可筛选的课程列表
- **搜索页** (`/search.tsx`): 课程搜索功能
- **评价页面**: 评价详情和评价编写

#### 2.1.3 核心组件
- `CourseDetailCard`: 展示课程详细信息（课号、学分、开课单位、教师组、评分等）
- `ReviewList`: 评价列表组件
- `ReviewFilter`: 评价筛选器（按学期、评分、排序方式）
- `CourseFilter`: 课程筛选器（按院系、类别）

#### 2.1.4 数据模型
```typescript
CourseDetail: {
  id, code, name, credit, department, categories,
  main_teacher, teacher_group, rating: {avg, count},
  related_courses, related_teachers
}

Review: {
  id, course, semester, rating, comment,
  created_at, modified_at, reactions, score
}
```

## 3. 镜像站架构设计

### 3.1 总体架构

```
镜像站架构:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   原站API      │────│  数据同步脚本     │────│  静态文件生成    │
│ (1.tongji.icu) │    │ (Python + API)   │    │ (JSON + HTML)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  数据存储&缓存    │    │  GitHub Pages   │
                       │ (JSON Files)     │    │  (MkDocs/Hugo)  │
                       └──────────────────┘    └─────────────────┘
```

### 3.2 静态站设计原则

#### 3.2.1 数据存储策略
由于镜像站是静态站点，不能使用数据库，采用以下存储方案：

1. **JSON文件存储**: 将课程和评价数据存储为结构化JSON文件
2. **文件分层**: 按功能和数据类型分层存储
3. **索引文件**: 创建索引文件加速查找和导航

#### 3.2.2 文件结构设计
```
docs/                          # MkDocs根目录
├── data/                      # 数据文件目录
│   ├── courses/              # 课程数据
│   │   ├── index.json       # 课程索引
│   │   ├── by-department/   # 按院系分类
│   │   ├── by-category/     # 按课程类别分类
│   │   └── details/         # 课程详情 {course_id}.json
│   ├── reviews/             # 评价数据
│   │   ├── index.json      # 评价索引
│   │   ├── by-course/      # 按课程分组
│   │   └── latest/         # 最新评价
│   ├── statistics/          # 统计数据
│   │   └── summary.json    # 网站统计摘要
│   └── filters/             # 筛选器数据
│       ├── departments.json
│       ├── categories.json
│       └── semesters.json
├── assets/                   # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
├── pages/                    # 静态页面
│   ├── courses/             # 课程页面
│   ├── reviews/             # 评价页面
│   └── search/              # 搜索页面
└── mkdocs.yml               # MkDocs配置
```

### 3.3 数据模型设计

#### 3.3.1 课程数据模型
```json
{
  "courses_index": {
    "total": 8451,
    "last_updated": "2024-01-01T00:00:00Z",
    "departments": ["计算机科学与工程学院", "数学科学学院", ...],
    "categories": ["专业必修", "专业选修", ...],
    "courses": [
      {
        "id": 29300,
        "code": "00200901",
        "name": "大学生创业基础",
        "department": "行政",
        "teacher": "裴培",
        "credit": 0,
        "categories": ["工程能力与创新思维"],
        "rating": {"count": 5, "avg": 3.4},
        "has_reviews": true,
        "last_review_time": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### 3.3.2 课程详情模型
```json
{
  "course_detail": {
    "id": 29300,
    "code": "00200901",
    "name": "大学生创业基础",
    "credit": 0,
    "department": "行政",
    "categories": ["工程能力与创新思维"],
    "main_teacher": {"name": "裴培", "tid": null},
    "teacher_group": [{"name": "裴培", "tid": null}],
    "rating": {"count": 5, "avg": 3.4},
    "reviews_summary": {
      "total": 5,
      "by_semester": [
        {"semester": "2023-2024-1", "count": 3, "avg": 3.7},
        {"semester": "2022-2023-2", "count": 2, "avg": 3.0}
      ],
      "by_rating": [
        {"rating": 5, "count": 1},
        {"rating": 4, "count": 2},
        {"rating": 3, "count": 1},
        {"rating": 2, "count": 1}
      ]
    },
    "related_courses": [],
    "related_teachers": []
  }
}
```

#### 3.3.3 评价数据模型
```json
{
  "course_reviews": {
    "course_id": 29300,
    "course_info": {
      "code": "00200901",
      "name": "大学生创业基础",
      "teacher": "裴培"
    },
    "total": 5,
    "reviews": [
      {
        "id": 12345,
        "rating": 4,
        "semester": "2023-2024-1",
        "comment": "课程内容有趣，老师讲解清晰",
        "score": "A",
        "created_at": "2024-01-01T00:00:00Z",
        "modified_at": "2024-01-01T00:00:00Z",
        "reactions": {"approves": 5, "disapproves": 1}
      }
    ]
  }
}
```

## 4. 数据更新策略

### 4.1 增量更新机制

#### 4.1.1 更新触发方式
1. **定时更新**: 每月自动同步（GitHub Actions）
2. **手动触发**: 支持手动触发更新
3. **差异检测**: 基于时间戳的增量更新

#### 4.1.2 更新流程
```
1. API数据获取
   ├── 获取课程列表 (分页)
   ├── 获取评价列表 (分页)
   └── 获取基础数据 (院系、学期等)

2. 差异检测
   ├── 比较现有数据时间戳
   ├── 识别新增/更新的课程
   └── 识别新增/更新的评价

3. 数据处理
   ├── 数据清洗和验证
   ├── 统计信息计算
   └── 索引文件更新

4. 静态文件生成
   ├── 生成JSON数据文件
   ├── 生成HTML页面
   └── 更新索引和导航

5. 部署更新
   ├── 提交到Git仓库
   └── 触发GitHub Pages部署
```

### 4.2 数据一致性保证

#### 4.2.1 版本控制
- 每次更新生成版本标识
- 保留数据更新历史
- 支持回滚机制

#### 4.2.2 错误处理
- API请求重试机制
- 数据验证和校验
- 异常情况记录和报告

## 5. 前端页面设计

### 5.1 页面结构

#### 5.1.1 主要页面
1. **首页** (`/`): 网站介绍、统计信息、快速导航
2. **课程列表** (`/courses/`): 分页显示所有课程，支持筛选
3. **课程详情** (`/courses/{course_id}/`): 课程详细信息和评价
4. **搜索页面** (`/search/`): 课程搜索功能
5. **统计页面** (`/statistics/`): 数据统计和可视化

#### 5.1.2 导航设计
- 顶部导航栏：主要功能入口
- 侧边栏：筛选器和快速导航
- 面包屑：页面路径导航
- 底部：版权信息和更新时间

### 5.2 响应式设计
- 移动端适配
- 平板端适配
- 桌面端优化

### 5.3 性能优化
- 懒加载
- 分页加载
- 缓存策略
- 搜索索引

## 6. 技术实现方案

### 6.1 静态站生成工具选择

#### 6.1.1 MkDocs方案（推荐）
- **优势**: 文档友好、主题丰富、插件生态完善
- **自定义**: 通过插件扩展搜索、导航等功能
- **部署**: 原生支持GitHub Pages

#### 6.1.2 替代方案
- **Hugo**: 构建速度快，但自定义复杂度高
- **Jekyll**: GitHub原生支持，但功能相对简单
- **VuePress**: Vue生态，适合现代前端开发

### 6.2 搜索功能实现

#### 6.2.1 客户端搜索
```javascript
// 基于Lunr.js的全文搜索
const searchIndex = lunr(function() {
  this.field('name', { boost: 10 })
  this.field('code', { boost: 8 })
  this.field('teacher', { boost: 6 })
  this.field('department', { boost: 4 })
  this.field('categories', { boost: 2 })

  courses.forEach(course => {
    this.add({
      id: course.id,
      name: course.name,
      code: course.code,
      teacher: course.teacher,
      department: course.department,
      categories: course.categories.join(' ')
    })
  })
})
```

#### 6.2.2 搜索索引生成
- 预处理课程数据生成搜索索引
- 支持中文分词和模糊匹配
- 实时搜索建议

### 6.3 数据可视化
- Chart.js: 评分分布、趋势图表
- D3.js: 复杂的统计可视化
- 院系课程分布饼图
- 评价趋势时间线

## 7. 部署与运维

### 7.1 GitHub Actions配置

#### 7.1.1 自动化流程
```yaml
name: Sync Mirror Site
on:
  schedule:
    - cron: '0 2 1 * *'  # 每月1号凌晨2点
  workflow_dispatch:     # 手动触发

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run sync script
        run: python src/sync_mirror_site.py
        env:
          COOKIES: ${{ secrets.TONGJI_COOKIES }}

      - name: Build site
        run: mkdocs build

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
```

### 7.2 监控与维护

#### 7.2.1 同步状态监控
- 同步成功/失败通知
- 数据质量检查
- 性能指标监控

#### 7.2.2 错误处理
- Cookie失效检测
- API限流处理
- 网络异常重试

## 8. 安全与合规

### 8.1 数据隐私
- 不存储用户个人信息
- 评价内容匿名化
- 遵循原站隐私政策

### 8.2 访问控制
- 合理的爬取频率
- 尊重原站robots.txt
- 避免对原站造成负担

### 8.3 版权声明
- 明确标注数据来源
- 提供原站链接
- 声明镜像性质

## 9. 优化建议

### 9.1 性能优化
- CDN加速
- 图片压缩
- 资源合并
- 缓存策略

### 9.2 用户体验
- 快速搜索响应
- 直观的导航设计
- 移动端优化
- 无障碍访问

### 9.3 功能扩展
- 高级筛选器
- 评价情感分析
- 课程推荐算法
- 数据导出功能

## 10. 风险评估

### 10.1 技术风险
- 原站API变更
- 数据格式调整
- 认证机制变化

### 10.2 法律风险
- 版权争议
- 数据使用合规
- 镜像站政策

### 10.3 维护风险
- 同步脚本维护
- GitHub Actions限制
- 存储空间限制

## 11. 实施计划

### 11.1 Phase 1: 基础架构（1-2周）
- [ ] 数据模型设计实现
- [ ] 基础同步脚本开发
- [ ] MkDocs站点搭建

### 11.2 Phase 2: 核心功能（2-3周）
- [ ] 完整数据同步实现
- [ ] 搜索功能开发
- [ ] 主要页面完成

### 11.3 Phase 3: 优化完善（1-2周）
- [ ] 性能优化
- [ ] UI/UX改进
- [ ] 自动化部署

### 11.4 Phase 4: 上线运维（持续）
- [ ] GitHub Actions配置
- [ ] 监控告警设置
- [ ] 文档完善

## 12. 总结

本设计方案基于对原站前端架构、数据库设计和API结构的深入分析，提出了一个完整的静态镜像站解决方案。该方案具有以下特点：

1. **技术合理性**: 采用静态站生成技术，无需服务器维护
2. **数据完整性**: 全面镜像原站核心数据和功能
3. **更新及时性**: 自动化的增量同步机制
4. **用户友好性**: 保持与原站一致的用户体验
5. **维护简便性**: 基于GitHub生态，运维成本低

该方案为后续的实施提供了清晰的技术路线和实现细节，确保镜像站的稳定性和可持续发展。