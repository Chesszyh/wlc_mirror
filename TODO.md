# tongji.icu 镜像站项目

## 项目概述

本项目为 `1.tongji.icu`（同济大学课程评价系统）创建镜像站，原评价系统基于交大的开源项目开发，代码位于根目录下`wlc_backend`, `wlc_frontend`。镜像站使用 MkDocs + GitHub Pages 构建，实现每月自动数据同步。

后续，该项目的数据会与另外一个项目：选课模拟系统结合，将由我来思考二者数据库结构的整合。

## 项目结构

- `refs/`: 参考资料和示例代码
- `src/`: 数据同步脚本和相关模块
- `tests/`: 测试脚本
- `examples/`: API调用示例与返回结果
- `wlc_backend/`: 原评价系统后端代码
- `wlc_frontend/`: 原评价系统前端代码
- `docs/`: MkDocs 文档目录

## TODO

### Agent-1

- [x] 根据cookie实现稳健的自动登录：参考`refs/simple_test.py`，该示例代码已经实现cf人机验证绕过
- [x] 参考`wlc_backend`的代码，根据`wlc_backend`的API和`wlc_backend/WIKI.md`：
  - [x] 学习并了解API的使用方法
  - [x] 编写尽可能多的API调用示例代码，要求输出美观清晰，帮我全面了解API的返回内容

### Agent-2

- [ ] 继续学习，并记忆另外一个项目：选课模拟系统`refs/exist_db_schema.sql`的数据库定义
- [ ] 学习`examples/apis_json`下的API返回的JSON文件，理解各个字段的含义
- [ ] 定义合理的数据模型:
  - [ ] 如何建立镜像站的数据库结构？你可同时给出`mkdocs`的`yaml`配置文件。
  - [ ] 如何在“选课模拟系统”的数据库基础上，添加必要的表和字段，以精确/模糊匹配`1.tongji.icu`的课程字段、并导入`1.tongji.icu`的课程评价？
    - [ ] 匹配规则如何？比如`api_course`中`"code": "00200902"`表示课号为`002009`的课程的第2个教学班，这种情况如何处理？

## 未来优化

1. **MkDocs 集成**: 基于同步数据生成静态站点
2. **GitHub Actions**: 实现自动化的每月数据同步
3. **CDN 优化**: 优化静态资源加载速度
4. **搜索功能**: 实现客户端搜索功能
5. **数据可视化**: 添加统计图表和趋势分析
