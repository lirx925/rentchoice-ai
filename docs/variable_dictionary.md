# 变量字典

## listings（CSV 导入时）

|变量|类型|含义/范围|
|---|---|---|
|listing_id|string|由标题、位置、面积和租金生成的稳定匿名标识|
|title|string|源数据房源标题，最多保留100字|
|district, subdistrict, community|string|由源位置文本拆分的区、板块、小区|
|monthly_rent|number|从房租文本解析的月租（元）|
|area_sqm|number|从面积文本解析的平方米数|
|metro_distance_m|number/null|从地铁描述解析的距离；缺失时为空|
|rental_type|category|whole / shared，由源租赁类型映射|
|source_rental_type|string|源文件中的整租/合租类型原文|
|bedrooms, living_rooms|number/null|从户型文本解析的室、厅数量|
|orientation|string/null|朝向原文|
|location_text, metro_info|string/null|源位置和地铁描述原文|
|data_source|string|数据来源说明|
|source_record_type|string|租赁挂牌记录（非成交记录）|
|data_quality_flag|category|eligible / outlier_excluded|
|commute_minutes 等未提供字段|null|源数据未提供，禁止伪造|

## participants（偏好提交时）

|变量|类型|含义/范围|
|---|---|---|
|participant_id|string|随机 UUID，匿名唯一键|
|created_at|datetime|UTC 创建时间|
|treatment_group|category|control / score_only / explained|
|budget_max, ideal_rent|integer|最高预算、理想月租（元）|
|destination_district|category|主要目的地区域；上海行政区或暂不确定/不限|
|min_area|integer|最低面积㎡，10–60|
|rental_type_preference|category|accept_shared / no_shared / no_preference|
|importance_rent, importance_location, importance_area, importance_metro|integer|重要性 1–5|
|importance_decoration, importance_community, importance_safety|integer|重要性 1–5|
|prior_rental_experience|boolean|是否有租房经历|
|initial_ai_trust|integer|初始 AI 信任 1–7|
|participant_status|category|本科生/研究生/实习生/已工作/其他|
|consent|boolean|是否同意匿名记录，必须为 true|

## choices（每轮提交时）

|变量|类型|含义/范围|
|---|---|---|
|participant_id| string|连接 participants|
|round_number|integer|轮次 1–6；与 participant_id 联合唯一|
|treatment_group|category|参与者固定实验条件|
|option_a_id, option_b_id, option_c_id|string|展示顺序中的三个房源 ID|
|recommended_listing_id|string|后台算法最高分房源；control 也记录|
|chosen_listing_id|string|用户选择的房源 ID|
|recommendation_followed|boolean|选择是否等于算法最高分|
|chosen_rent, chosen_area|number|所选房源的租金和面积|
|chosen_commute|null|保留兼容字段；当前真实数据不记录固定通勤时间|
|chosen_location_match|float|所选房源的位置匹配分，40/50/100|
|willingness_to_pay|integer|最高支付意愿，1000–10000 元|
|satisfaction, choice_confidence|integer|满意度、信心 1–7|
|decision_time_seconds|float|本轮非负决策秒数|
|chosen_utility, best_available_utility|float|0–100 声明偏好代理效用|
|welfare_loss|float|非负代理福利损失|
|created_at|datetime|UTC 保存时间|

## post_survey（结束问卷提交时）

|变量|类型|含义/范围|
|---|---|---|
|participant_id|string|匿名唯一键|
|perceived_helpfulness|integer|感知帮助 1–7；control 指排序帮助|
|final_ai_trust|integer|最终信任 1–7|
|perceived_accuracy|integer|感知准确 1–7|
|willingness_to_use_again|integer|再次使用意愿 1–7|
|comments|string|可选意见，最多 200 字|
|created_at|datetime|UTC 保存时间|
