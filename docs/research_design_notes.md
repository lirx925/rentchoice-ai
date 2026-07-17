# 初步经济学研究设计

## 研究问题与机制

个性化 AI 推荐和解释是否能够降低大学生租房搜索成本、改善住房匹配，还是会通过算法信任和锚定效应改变消费者选择？参与者随机进入 control、score_only 或 explained，完成六轮模拟三选一任务。

## 假设

- H1：显示 AI 推荐将提高用户选择算法推荐房源的概率。
- H2：带个性化解释的推荐比仅显示推荐分数具有更高的服从率。
- H3：AI 推荐将缩短平均决策时间。
- H4：AI 推荐可能降低基于声明偏好计算的福利损失。
- H5：AI 推荐也可能提高用户对推荐房源的最高支付意愿。

主要结果变量为 `recommendation_followed`、`decision_time_seconds`、`willingness_to_pay`、`satisfaction`、`welfare_loss` 和 `final_ai_trust`。

基本回归可写为：

`Y_ir = α + β1 ScoreOnly_i + β2 Explained_i + round fixed effects + ε_ir`

其中 i 表示参与者，r 表示选择轮次，control 为基准组。标准误可在参与者层面聚类。可扩展检验初始 AI 信任、是否有租房经验和预算约束的异质性，但应标注探索性。

`chosen_utility` 直接使用声明偏好加权推荐分数，`best_available_utility` 是本轮三套房源的最高分，`welfare_loss=max(0,best-chosen)`。该指标只是基于声明偏好和研究者设定函数构造的代理指标，不等同于现实中的真实消费者福利，也未纳入搬家成本、议价、房屋真实性等未观测因素。

课程项目样本量可能较小，结果仅用于探索性分析，不应作因果结论的过度外推。未来正式研究需要伦理审批、预注册、功效分析、更大样本、数据保留期限和退出/删除机制。不得伪造实验结果。

