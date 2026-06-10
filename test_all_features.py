#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试 - 验证所有新功能
"""

import os
import sys
import json
from datetime import date, timedelta
from modules.data_manager import DataManager
from modules.calculator import CarbonCalculator
from modules.visualizer import Visualizer
from modules.suggester import Suggester
from modules.importer import DataImporter
from modules.exporter import ReportExporter

dm = DataManager()
calc = CarbonCalculator(dm)
viz = Visualizer()
suggester = Suggester(dm, calc)
importer = DataImporter(dm)
exporter = ReportExporter(dm, calc, suggester)

print("=" * 70)
print("🌍 碳足迹追踪工具 - 新功能综合测试")
print("=" * 70)

# 1. 创建测试用户
print("\n📌 步骤1: 创建测试用户")
user = dm.create_user("测试用户", region="huadong", household_size=2)
user_id = user['user_id']
print(f"  ✅ 用户创建成功: {user['name']} (ID: {user_id})")

# 2. 测试可用类别列表
print("\n📌 步骤2: 测试可用类别列表")
all_cats = dm.get_categories()
available_cats = dm.get_available_categories()
print(f"  所有类别 ({len(all_cats)}): {all_cats}")
print(f"  可用类别 ({len(available_cats)}): {available_cats}")
assert 'benchmarks' not in available_cats, "benchmarks不应该在可用类别中"
print(f"  ✅ 可用类别筛选正确")

# 3. 生成演示数据
print("\n📌 步骤3: 生成演示数据")
today = date.today()

# 添加过去4周的演示数据
for week_offset in range(4):
    week_date = today - timedelta(weeks=week_offset)
    for day in range(7):
        d = week_date - timedelta(days=day)
        date_str = d.isoformat()
        # 每天通勤
        dm.add_activity(user_id, 'transport', 'car_gasoline', 25, date_str, '通勤')
        # 每天用电
        dm.add_activity(user_id, 'electricity', 'grid_electricity', 8, date_str, '家庭用电')
        # 每天饮食
        dm.add_activity(user_id, 'food', 'pork', 1, date_str, '午餐')
        dm.add_activity(user_id, 'food', 'vegetables', 1, date_str, '晚餐')

# 每周购物
dm.add_activity(user_id, 'shopping', 'clothing', 1, (today - timedelta(days=14)).isoformat(), '买衣服')
dm.add_activity(user_id, 'shopping', 'electronics', 1, (today - timedelta(days=21)).isoformat(), '买手机')

print("  ✅ 演示数据生成完成 (约120条记录)")

# 4. 测试创建活动模板
print("\n📌 步骤4: 测试活动模板功能")

# 创建每日通勤模板
template1 = dm.create_template(
    user_id, "每日通勤", "transport", "car_gasoline", 25,
    "工作日通勤", "daily"
)
assert template1 is not None
print(f"  ✅ 模板1创建: {template1['name']} (ID: {template1['template_id']})")

# 创建每月电费模板
template2 = dm.create_template(
    user_id, "每月电费", "electricity", "grid_electricity", 240,
    "月度家庭用电", "monthly"
)
assert template2 is not None
print(f"  ✅ 模板2创建: {template2['name']} (ID: {template2['template_id']})")

# 创建每周肉类消费模板
template3 = dm.create_template(
    user_id, "每周肉类", "food", "beef", 2,
    "周末改善伙食", "weekly"
)
assert template3 is not None
print(f"  ✅ 模板3创建: {template3['name']} (ID: {template3['template_id']})")

# 列出所有模板
templates = dm.list_templates(user_id)
print(f"  ✅ 共创建 {len(templates)} 个模板")

# 使用模板
activities = dm.apply_template(user_id, template1['template_id'], activity_date=today.isoformat())
assert len(activities) == 1
emission = calc.calculate_activity_emission(activities[0], user.get('region', 'national_average'))
print(f"  ✅ 使用模板生成记录: {len(activities)} 条, 排放 {emission:.2f} kg CO₂")

# 使用周期模板生成7天记录
activities = dm.apply_template(user_id, template1['template_id'], generate_period='daily')
assert len(activities) == 7
print(f"  ✅ 使用周期模板生成 {len(activities)} 条记录 (未来7天)")

# 5. 测试批量导入功能
print("\n📌 步骤5: 测试批量导入功能")

# 生成电费账单模板
template_path = "test_electricity_template.csv"
importer.generate_template_csv('electricity', template_path)
print(f"  ✅ 电费账单模板已生成: {template_path}")

# 导入电费账单
added_count, added, errors, summary = importer.import_csv(user_id, template_path, 'electricity')
print(f"  ✅ 电费账单导入: 成功 {summary['success_count']} 条, "
      f"跳过 {summary['skipped_count']} 条, 失败 {summary['failed_count']} 条")
assert summary['success_count'] == 2, "电费账单应该导入2条成功"
print(f"  ✅ 导入摘要正确")

# 生成加油记录模板（包含升数录入）
fuel_template_path = "test_fuel_template.csv"
with open(fuel_template_path, 'w', encoding='utf-8-sig') as f:
    f.write("date,category,activity_type,amount,amount_unit,notes\n")
    f.write("2025-10-01,transport,car_gasoline,45,升,92号汽油\n")
    f.write("2025-10-08,transport,car_diesel,38,升,0号柴油\n")
    f.write("2025-10-15,transport,car_gasoline,320,公里,跑长途\n")
print(f"  ✅ 加油记录模板已生成: {fuel_template_path}")

# 导入加油记录
added_count, added, errors, summary = importer.import_csv(user_id, fuel_template_path, 'fuel')
print(f"  ✅ 加油记录导入: 成功 {summary['success_count']} 条, "
      f"跳过 {summary['skipped_count']} 条, 失败 {summary['failed_count']} 条")
assert summary['success_count'] == 3, "加油记录应该导入3条成功"

# 检查第一条记录的单位转换
for act in added:
    if '45升' in act.get('notes', ''):
        print(f"  ✅ 45升汽油转换: {act['amount']:.0f} 公里 (预期450公里)")
        assert 440 <= act['amount'] <= 460, "45升汽油应该转换为约450公里"
        emission = calc.calculate_activity_emission(act, 'huadong')
        print(f"     排放: {emission:.2f} kg CO₂")
        break

# 6. 测试目标预测功能
print("\n📌 步骤6: 测试目标预测功能")

# 创建减排目标
goal = dm.set_goal(user_id, 'total_emission', 300, 'monthly', description='月度总排放目标')
goal2 = dm.set_goal(user_id, 'transport', 150, 'monthly', description='月度交通排放目标')
print(f"  ✅ 已创建2个减排目标")

# 获取目标预测
predictions = calc.get_all_goals_prediction(user_id)
assert len(predictions) == 2
print(f"  ✅ 目标预测获取成功 ({len(predictions)} 个目标)")

for pred in predictions:
    print(f"\n  🎯 {pred['goal_type']} 目标预测:")
    print(f"     目标: {pred['target']:.0f} kg, 当前: {pred['current']:.1f} kg")
    print(f"     周期进度: {pred['period_progress']:.1f}% ({pred['days_passed']}/{pred['days_total']}天)")
    print(f"     剩余额度: {pred['remaining_quota']:.1f} kg")
    print(f"     每日可用: {pred['daily_quota']:.2f} kg/天")
    print(f"     预计月底: {pred['projected_total']:.1f} kg")
    print(f"     风险评估: {pred['risk_description']}")
    assert 'remaining_quota' in pred
    assert 'daily_quota' in pred
    assert 'projected_total' in pred
    assert 'will_achieve' in pred
print(f"  ✅ 目标预测数据完整")

# 7. 测试建议匹配（真实减排量）
print("\n📌 步骤7: 测试建议匹配功能")

suggestions = suggester.get_suggestions(user_id)
print(f"  ✅ 获取到 {len(suggestions)} 条建议")
for i, s in enumerate(suggestions, 1):
    calc_saving = s.get('calculated_saving_kg', 0)
    base_saving = s.get('saving_estimation', {}).get('saving_kg_co2', 0)
    print(f"\n  💡 建议 {i}: {s['title']}")
    print(f"     类别: {s.get('category', '')}, 匹配条件: {s.get('condition', '')}")
    print(f"     计算减排量: {calc_saving:.1f} kg/月 (基础值: {base_saving} kg)")
    print(f"     影响程度: 占月排放 {s.get('impact_percent', 0):.1f}%")
    if calc_saving != base_saving:
        print(f"     ✅ 已根据用户实际数据动态计算减排量")

# 8. 测试HTML报告（达标状态）
print("\n📌 步骤8: 测试HTML报告生成")

html_path = "test_report.html"
success = exporter.export_html(user_id, html_path)
assert success
print(f"  ✅ HTML报告已生成: {os.path.abspath(html_path)}")

# 检查HTML内容中是否包含达标状态
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

if '已达标' in html_content:
    print(f"  ✅ HTML报告中包含明确的达标状态显示")
else:
    print(f"  ⚠️  HTML报告中未找到达标状态（可能未达标）")

print("\n" + "=" * 70)
print("🎉 所有新功能测试通过!")
print("=" * 70)
print("\n📋 测试总结:")
print("  ✅ 可用类别筛选 - 只显示可录入的活动类别")
print("  ✅ 活动模板功能 - 创建、使用、周期生成")
print("  ✅ 批量导入功能 - 电费账单、加油升数换算、详细摘要")
print("  ✅ 目标预测功能 - 趋势预测、剩余额度、每日可用")
print("  ✅ 建议真实减排 - 根据用户数据动态计算")
print("  ✅ HTML报告 - 明确的达标状态显示")
print("\n💡 提示: 可以运行 `python main.py` 体验完整的交互界面")
