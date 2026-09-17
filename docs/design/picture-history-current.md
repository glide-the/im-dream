<!-- [Input] Three public current-user picture routes and Admin Registry103 list/full contracts. -->
<!-- [Output] Current picture-history product rules, state handling, failures and acceptance. -->
<!-- [Pos] Current design source for owner-only historical picture reads; friendship access is separate. -->
<!-- [Sync] 2026-09-15: replace Dream PostgreSQL reads with two strict Admin operations. -->

# 当前用户图片历史

## 背景与问题

Timeline通过`/api/pictures`、`/api/pictures/range`和`/api/pictures/{date}/full`读取当前用户已保存的历史图片。旧实现由三个Dream `database.py` helper直接查询`daily_pictures`，使公开请求依赖Dream PostgreSQL连接，也把身份选择、范围过滤和图片选择分散在路由与SQL中。

Admin已有好友图片接口，但好友读取要求accepted关系，不能用于当前用户读取。当前用户历史需要独立的owner权限判断。

## 目标与边界

Dream保留三个公开路径、请求参数和响应结构。Admin Registry103提供`picture-history.list`与`picture-history.full`，从OAuth principal取得当前用户并完成数据读取。Dream只验证公开参数、构造闭合DTO和映射既有响应。

本功能只读已有图片，不生成、重绘、保存或删除图片，不修改好友关系、Runtime、共享文件或数据库schema。好友Timeline与好友full图继续使用独立的friendship operation和权限规则。

## 概念与规则

`picture-history.list`接收nullable `start_date`、nullable `end_date`和非负JSON safe integer `limit`。空白日期规范化为null；非空日期必须是canonical `YYYY-MM-DD`。范围双端包含，结果按日期倒序。Admin优先返回thumbnail，thumbnail为null时返回原图。

普通列表把null或空prompt映射为`""`，保持原公开行为；范围列表保留nullable prompt。两条列表路径均返回`{pictures:[{date,base64,prompt,created_at}]}`，其中`created_at`为带时区的ISO时间或null。

`picture-history.full`只接收一个canonical日期。Admin按当前owner与日期查找，并在同日多条记录中返回创建时间最新的原图。无记录返回null；Dream把null或空字符串映射为`404 Picture not found for this date`。

## 正常流程

1. Dream用当前Bearer完成OAuth身份认证并要求`dream:read`。
2. Dream验证日期与limit，构造不含用户ID、好友ID或物理数据库选择器的DTO。
3. Consumer检查Registry103 operation hash与identity/unified schema capability。
4. Admin在一个只读UOW内按principal限制owner并执行范围、排序或同日最新选择。
5. Dream映射普通列表prompt或full 404，返回既有公开结构。

## 状态与失败

该流程不改变持久化状态。请求依次处于参数校验、身份认证、capability检查、Admin读取和公开投影阶段；任一阶段失败即终止。

- 日期非法返回固定`400 Invalid date format, expected YYYY-MM-DD`。
- limit为负数、超过JSON safe integer或不是整数时返回422。
- full没有图片时返回固定404。
- OAuth缺失、scope不足、entity grant、capability缺失、Admin超时或响应DTO非法时返回明确错误。
- 失败不得查询Dream PostgreSQL，不得改用friendship接口，也不得把权限或传输错误转换为空列表。

## 影响范围与验收

影响范围限于三个public route、统一Pydantic consumer、RequestAuth operation注册和对应文档。验收要求普通/范围列表共享同一list operation，保留prompt差异、范围边界、thumbnail fallback后的字段、nullable精确时间和full 404；三个旧helper被设为抛错时公开路由仍通过fake Admin返回。AST检查必须确认`routers/pictures.py`没有legacy database import或三个helper调用。
