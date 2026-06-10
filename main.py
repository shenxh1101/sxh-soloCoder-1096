#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个人碳足迹追踪与减排建议工具
Carbon Footprint Tracker & Reduction Suggestion Tool
"""

import os
import sys
from datetime import date, datetime

from modules.data_manager import DataManager
from modules.calculator import CarbonCalculator
from modules.visualizer import Visualizer
from modules.suggester import Suggester
from modules.importer import DataImporter
from modules.exporter import ReportExporter


class CarbonTrackerCLI:
    def __init__(self):
        self.dm = DataManager()
        self.calc = CarbonCalculator(self.dm)
        self.viz = Visualizer()
        self.suggester = Suggester(self.dm, self.calc)
        self.importer = DataImporter(self.dm)
        self.exporter = ReportExporter(self.dm, self.calc, self.suggester)
        self.current_user = None

    def banner(self):
        logo = '''
╔══════════════════════════════════════════════════════════════╗
║              🌍  个人碳足迹追踪与减排建议工具  🌱            ║
║            Carbon Footprint Tracker & Advisor               ║
╠══════════════════════════════════════════════════════════════╣
║  追踪日常排放 · 分析碳足迹 · 个性化建议 · 践行低碳生活        ║
╚══════════════════════════════════════════════════════════════╝
'''
        print(logo)

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def input_prompt(self, prompt, default=None, required=False, validator=None):
        while True:
            display_prompt = f"{prompt}"
            if default is not None:
                display_prompt += f" [{default}]"
            display_prompt += ": "

            try:
                user_input = input(display_prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print("\n已取消")
                return None

            if not user_input:
                if default is not None:
                    return default
                if required:
                    print("  ⚠️  此项为必填，请输入内容")
                    continue
                return None

            if validator and not validator(user_input):
                print("  ⚠️  输入格式无效，请重新输入")
                continue

            return user_input

    def confirm_prompt(self, prompt, default=False):
        default_str = 'Y/n' if default else 'y/N'
        while True:
            try:
                user_input = input(f"{prompt} [{default_str}]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return False

            if not user_input:
                return default
            if user_input in ['y', 'yes', '是']:
                return True
            if user_input in ['n', 'no', '否']:
                return False
            print("  ⚠️  请输入 y/n 或 是/否")

    def select_from_list(self, items, prompt, display_func=None, allow_back=True):
        if not items:
            print("  📭 暂无数据")
            return None

        while True:
            print(f"\n  {prompt}:")
            for idx, item in enumerate(items, 1):
                if display_func:
                    display = display_func(item)
                else:
                    display = str(item)
                print(f"  [{idx}] {display}")
            if allow_back:
                print(f"  [0] ← 返回")

            try:
                choice = input(f"\n  请选择编号: ").strip()
            except (EOFError, KeyboardInterrupt):
                return None

            if not choice:
                continue
            try:
                idx = int(choice)
                if idx == 0 and allow_back:
                    return None
                if 1 <= idx <= len(items):
                    return items[idx - 1]
                print("  ⚠️  无效的编号，请重新选择")
            except ValueError:
                print("  ⚠️  请输入有效的数字编号")

    # ==================== 用户管理 ====================

    def menu_user_management(self):
        while True:
            self.clear_screen()
            self.banner()
            print(self.viz.section('👥 用户档案管理', 62))
            print("  [1] 查看所有用户")
            print("  [2] 创建新用户档案")
            print("  [3] 切换当前用户")
            print("  [4] 编辑用户信息")
            print("  [5] 删除用户档案")
            print("  [0] 返回主菜单")

            if self.current_user:
                print(f"\n  👤 当前用户: {self.current_user['name']} (ID: {self.current_user['user_id']})")

            choice = input("\n  请选择操作: ").strip()

            if choice == '1':
                self.list_all_users()
            elif choice == '2':
                self.create_user()
            elif choice == '3':
                self.switch_user()
            elif choice == '4':
                self.edit_user()
            elif choice == '5':
                self.delete_user()
            elif choice == '0':
                return
            else:
                print("  ⚠️  无效的选择")

            input("\n  按 Enter 继续...")

    def list_all_users(self):
        users = self.dm.list_users()
        if not users:
            print("\n  📭 暂无用户档案，请先创建")
            return

        print(f"\n  📋 共找到 {len(users)} 个用户档案:")
        print("  " + "─" * 70)
        print(f"  {'编号':<4} {'ID':<10} {'姓名':<12} {'地区':<10} {'人数':<6} {'活动数':<8}")
        print("  " + "─" * 70)
        for idx, u in enumerate(users, 1):
            print(f"  [{idx:<2}] {u['user_id']:<10} {u['name']:<12} "
                  f"{u.get('region', '-'):<10} {u.get('household_size', 1):<6} "
                  f"{u.get('activity_count', 0):<8}")
        print("  " + "─" * 70)

    def create_user(self):
        print("\n  📝 创建新用户档案")
        print("  " + "─" * 40)

        name = self.input_prompt("  姓名/昵称", required=True)
        if name is None:
            return

        regions = self.dm.get_activity_types('electricity')
        region_map = {r['key']: r['name'] for r in regions}

        print("\n  请选择所在地区（用于电力碳排放因子）:")
        region_items = list(region_map.items())
        for idx, (key, rname) in enumerate(region_items, 1):
            print(f"  [{idx}] {rname}")

        while True:
            region_choice = self.input_prompt("  选择编号", default=str(len(region_items)))
            try:
                idx = int(region_choice) - 1
                if 0 <= idx < len(region_items):
                    region = region_items[idx][0]
                    break
            except (ValueError, TypeError):
                pass
            print("  ⚠️  无效的选择")

        household_size = self.input_prompt("  家庭人数", default="1",
                                            validator=lambda x: x.isdigit() and int(x) > 0)
        household_size = int(household_size) if household_size else 1

        description = self.input_prompt("  备注说明（可选）")

        user = self.dm.create_user(name, region, household_size, description or '')
        print(f"\n  ✅ 用户档案创建成功!")
        print(f"     ID: {user['user_id']}")
        print(f"     姓名: {user['name']}")

        if self.confirm_prompt("  是否切换到此用户?", default=True):
            self.current_user = user
            print("  ✅ 已切换当前用户")

    def switch_user(self):
        users = self.dm.list_users()
        if not users:
            print("\n  📭 暂无用户档案")
            return

        selected = self.select_from_list(
            users,
            "选择要切换的用户",
            display_func=lambda u: f"{u['name']} ({u['user_id']}) - {u.get('activity_count', 0)} 条记录"
        )
        if selected:
            self.current_user = self.dm.get_user(selected['user_id'])
            print(f"\n  ✅ 已切换到用户: {self.current_user['name']}")

    def edit_user(self):
        if not self.current_user:
            print("\n  ⚠️  请先选择当前用户")
            return

        print(f"\n  ✏️  编辑用户: {self.current_user['name']}")
        print("  (直接回车保留原有值)")
        print("  " + "─" * 40)

        name = self.input_prompt("  姓名/昵称", default=self.current_user['name'])
        if name is None:
            return

        regions = self.dm.get_activity_types('electricity')
        region_names = {r['key']: r['name'] for r in regions}
        current_region_name = region_names.get(self.current_user.get('region', 'national_average'), '全国平均')
        print(f"\n  当前地区: {current_region_name}")

        region_items = list(region_names.items())
        for idx, (key, rname) in enumerate(region_items, 1):
            marker = " ← 当前" if key == self.current_user.get('region') else ""
            print(f"  [{idx}] {rname}{marker}")

        region = self.current_user.get('region', 'national_average')
        region_choice = self.input_prompt("  选择新地区编号（回车不修改）")
        if region_choice:
            try:
                idx = int(region_choice) - 1
                if 0 <= idx < len(region_items):
                    region = region_items[idx][0]
            except (ValueError, TypeError):
                print("  ⚠️  地区未修改")

        hh_default = str(self.current_user.get('household_size', 1))
        household_size = self.input_prompt("  家庭人数", default=hh_default,
                                            validator=lambda x: x.isdigit() and int(x) > 0)
        household_size = int(household_size) if household_size else self.current_user.get('household_size', 1)

        description = self.input_prompt("  备注说明", default=self.current_user.get('description', ''))

        updated = self.dm.update_user(
            self.current_user['user_id'],
            name=name, region=region,
            household_size=household_size,
            description=description or ''
        )
        if updated:
            self.current_user = updated
            print("\n  ✅ 用户信息已更新")

    def delete_user(self):
        users = self.dm.list_users()
        if not users:
            print("\n  📭 暂无用户档案")
            return

        selected = self.select_from_list(
            users,
            "选择要删除的用户",
            display_func=lambda u: f"{u['name']} ({u['user_id']})"
        )
        if not selected:
            return

        if not self.confirm_prompt(f"  ⚠️  确定要删除用户 '{selected['name']}' 的所有数据吗？此操作不可恢复!",
                                    default=False):
            print("  已取消删除")
            return

        if self.dm.delete_user(selected['user_id']):
            if self.current_user and self.current_user['user_id'] == selected['user_id']:
                self.current_user = None
            print(f"\n  ✅ 用户 '{selected['name']}' 已删除")

    # ==================== 活动记录 ====================

    def menu_activity_management(self):
        if not self.current_user:
            print("\n  ⚠️  请先选择用户档案")
            return

        while True:
            self.clear_screen()
            self.banner()
            print(self.viz.section(f'📊 活动记录管理 - {self.current_user["name"]}', 62))
            print("  [1] 记录新活动")
            print("  [2] 使用常用活动模板")
            print("  [3] 管理常用活动模板")
            print("  [4] 查看活动历史")
            print("  [5] 删除活动记录")
            print("  [6] 批量导入数据(CSV)")
            print("  [7] 下载导入模板")
            print("  [0] 返回主菜单")

            choice = input("\n  请选择操作: ").strip()

            if choice == '1':
                self.add_activity_wizard()
            elif choice == '2':
                self.use_activity_template()
            elif choice == '3':
                self.manage_activity_templates()
            elif choice == '4':
                self.view_activity_history()
            elif choice == '5':
                self.delete_activity()
            elif choice == '6':
                self.bulk_import_data()
            elif choice == '7':
                self.download_templates()
            elif choice == '0':
                return
            else:
                print("  ⚠️  无效的选择")

            input("\n  按 Enter 继续...")

    def add_activity_wizard(self):
        print(f"\n  ➕ 记录新活动")
        print("  " + "─" * 50)

        categories = self.dm.get_available_categories()
        category_names = self.calc.CATEGORY_NAMES

        cat_items = [{'key': c, 'name': category_names.get(c, c)} for c in categories]

        print("\n  选择活动类别:")
        for idx, cat in enumerate(cat_items, 1):
            print(f"  [{idx}] {cat['name']}")

        while True:
            choice = self.input_prompt("  输入类别编号", required=True)
            if choice is None:
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(cat_items):
                    category = cat_items[idx]['key']
                    break
            except (ValueError, TypeError):
                pass
            print("  ⚠️  无效的选择")

        types = self.dm.get_activity_types(category)
        if category == 'electricity' and not types:
            types = [{'key': 'grid_electricity', 'name': '家庭用电',
                      'factor': 0.581, 'unit': 'kWh',
                      'serving_size': 1.0}]
        if not types:
            print("  ⚠️  此类别暂无可选活动类型")
            return

        print(f"\n  选择具体活动类型:")
        for idx, t in enumerate(types, 1):
            print(f"  [{idx}] {t['name']} ({t['factor']} {t['unit']})")

        while True:
            choice = self.input_prompt("  输入类型编号", required=True)
            if choice is None:
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(types):
                    activity_type = types[idx]['key']
                    activity_type_name = types[idx]['name']
                    break
            except (ValueError, TypeError):
                pass
            print("  ⚠️  无效的选择")

        while True:
            amount_str = self.input_prompt(f"  请输入{activity_type_name}的数量", required=True)
            if amount_str is None:
                return
            try:
                amount = float(amount_str)
                if amount < 0:
                    print("  ⚠️  数量不能为负数")
                    continue
                break
            except ValueError:
                print("  ⚠️  请输入有效的数字")

        default_date = date.today().isoformat()
        activity_date = self.input_prompt("  活动日期 (YYYY-MM-DD)", default=default_date,
                                            validator=lambda x: self._validate_date(x))

        notes = self.input_prompt("  备注说明 (可选)")

        activity = self.dm.add_activity(
            self.current_user['user_id'],
            category=category,
            activity_type=activity_type,
            amount=amount,
            activity_date=activity_date,
            notes=notes or ''
        )

        if activity:
            region = self.current_user.get('region', 'national_average')
            emission = self.calc.calculate_activity_emission(activity, region)
            print(f"\n  ✅ 活动记录已添加!")
            print(f"     碳排放: {emission:.2f} kg CO₂")

    def _validate_date(self, date_str: str) -> bool:
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def use_activity_template(self):
        user_id = self.current_user['user_id']
        templates = self.dm.list_templates(user_id)

        if not templates:
            print("\n  📭 暂无常用活动模板，请先在「管理常用活动模板」中创建")
            return

        category_names = self.calc.CATEGORY_NAMES

        print(f"\n  📋 使用常用活动模板")
        print("  " + "─" * 50)

        def display_template(t):
            cat_name = category_names.get(t['category'], t['category'])
            type_name = self._get_type_name(t['category'], t['activity_type'])
            period_names = {'on_demand': '按需', 'daily': '每日', 'weekly': '每周', 'monthly': '每月'}
            period = period_names.get(t.get('period', 'on_demand'), t.get('period', ''))
            used = t.get('usage_count', 0)
            return f"{t['name']} ({cat_name} - {type_name}) [{period}] 常用: {used}次"

        selected = self.select_from_list(templates, "选择要使用的模板",
                                          display_func=display_template)
        if not selected:
            return

        template = selected
        print(f"\n  模板: {template['name']}")
        print(f"  类别: {category_names.get(template['category'], template['category'])}")
        print(f"  类型: {self._get_type_name(template['category'], template['activity_type'])}")
        print(f"  默认数量: {template['default_amount']}")

        amount_str = self.input_prompt("  数量 (回车使用默认值)",
                                        default=str(template['default_amount']))
        if amount_str is None:
            return
        try:
            amount = float(amount_str)
        except ValueError:
            amount = template['default_amount']

        notes = self.input_prompt("  备注 (回车使用默认值)",
                                    default=template.get('default_notes', ''))
        if notes is None:
            return

        default_date = date.today().isoformat()
        activity_date = self.input_prompt("  活动日期 (YYYY-MM-DD)",
                                            default=default_date,
                                            validator=lambda x: self._validate_date(x))
        if not activity_date:
            return

        period = template.get('period', 'on_demand')
        generate_period = None
        if period in ['daily', 'weekly']:
            if period == 'daily':
                msg = f"  是否生成未来7天的记录？"
            else:
                msg = f"  是否生成本周每天的记录？"
            if self.confirm_prompt(msg, default=False):
                generate_period = period

        activities = self.dm.apply_template(user_id, template['template_id'],
                                             custom_amount=amount,
                                             custom_notes=notes,
                                             activity_date=activity_date,
                                             generate_period=generate_period)

        if activities:
            region = self.current_user.get('region', 'national_average')
            total_emission = sum(
                self.calc.calculate_activity_emission(act, region) for act in activities
            )
            print(f"\n  ✅ 已成功生成 {len(activities)} 条记录!")
            print(f"     总碳排放: {total_emission:.2f} kg CO₂")
        else:
            print("\n  ❌ 生成记录失败")

    def manage_activity_templates(self):
        user_id = self.current_user['user_id']
        category_names = self.calc.CATEGORY_NAMES

        while True:
            self.clear_screen()
            self.banner()
            print(self.viz.section(f'📋 常用活动模板管理 - {self.current_user["name"]}', 62))

            templates = self.dm.list_templates(user_id)
            print(f"\n  已有模板: {len(templates)} 个")
            if templates:
                print("  " + "─" * 70)
                for t in templates:
                    cat_name = category_names.get(t['category'], t['category'])
                    type_name = self._get_type_name(t['category'], t['activity_type'])
                    period_names = {'on_demand': '按需', 'daily': '每日', 'weekly': '每周', 'monthly': '每月'}
                    period = period_names.get(t.get('period', 'on_demand'), t.get('period', ''))
                    print(f"  [{t['template_id']}] {t['name']}")
                    print(f"      {cat_name} - {type_name} | 默认: {t['default_amount']} | [{period}]")
                    if t.get('last_used_at'):
                        print(f"      已使用 {t.get('usage_count', 0)} 次 | 上次: {t['last_used_at'][:10]}")
                print("  " + "─" * 70)

            print("\n  [1] 创建新模板")
            print("  [2] 修改模板")
            print("  [3] 删除模板")
            print("  [0] 返回")

            choice = input("\n  请选择操作: ").strip()

            if choice == '1':
                self._create_template_wizard(user_id)
            elif choice == '2':
                self._update_template_wizard(user_id, templates)
            elif choice == '3':
                self._delete_template_wizard(user_id, templates)
            elif choice == '0':
                return
            else:
                print("  ⚠️  无效的选择")

            input("\n  按 Enter 继续...")

    def _create_template_wizard(self, user_id):
        print(f"\n  ➕ 创建新模板")
        print("  " + "─" * 50)

        name = self.input_prompt("  模板名称 (如: 每日通勤)", required=True)
        if not name:
            return

        categories = self.dm.get_available_categories()
        category_names = self.calc.CATEGORY_NAMES
        cat_items = [{'key': c, 'name': category_names.get(c, c)} for c in categories]

        print("\n  选择活动类别:")
        for idx, cat in enumerate(cat_items, 1):
            print(f"  [{idx}] {cat['name']}")

        while True:
            choice = self.input_prompt("  输入类别编号", required=True)
            if not choice:
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(cat_items):
                    category = cat_items[idx]['key']
                    break
            except ValueError:
                pass
            print("  ⚠️  无效的选择")

        types = self.dm.get_activity_types(category)
        if category == 'electricity' and not types:
            types = [{'key': 'grid_electricity', 'name': '家庭用电',
                      'factor': 0.581, 'unit': 'kWh', 'serving_size': 1.0}]

        print(f"\n  选择具体活动类型:")
        for idx, t in enumerate(types, 1):
            print(f"  [{idx}] {t['name']} ({t['factor']} {t['unit']})")

        while True:
            choice = self.input_prompt("  输入类型编号", required=True)
            if not choice:
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(types):
                    activity_type = types[idx]['key']
                    break
            except ValueError:
                pass
            print("  ⚠️  无效的选择")

        default_amount = None
        while True:
            amount_str = self.input_prompt("  默认数量", required=True)
            if amount_str is None:
                return
            try:
                default_amount = float(amount_str)
                if default_amount > 0:
                    break
                print("  ⚠️  数量必须大于0")
            except ValueError:
                print("  ⚠️  请输入有效的数字")

        default_notes = self.input_prompt("  默认备注 (可选)", default='')
        if default_notes is None:
            return

        print("\n  选择使用周期:")
        print("  [1] 按需使用 (默认)")
        print("  [2] 每日")
        print("  [3] 每周")
        print("  [4] 每月")

        period_choice = self.input_prompt("  请选择", default="1")
        period_map = {'1': 'on_demand', '2': 'daily', '3': 'weekly', '4': 'monthly'}
        period = period_map.get(period_choice, 'on_demand')

        template = self.dm.create_template(user_id, name, category, activity_type,
                                           default_amount, default_notes, period)
        if template:
            print(f"\n  ✅ 模板创建成功! ID: {template['template_id']}")
        else:
            print("\n  ❌ 模板创建失败")

    def _update_template_wizard(self, user_id, templates):
        if not templates:
            print("\n  📭 暂无模板可修改")
            return

        def display_template(t):
            category_names = self.calc.CATEGORY_NAMES
            cat_name = category_names.get(t['category'], t['category'])
            type_name = self._get_type_name(t['category'], t['activity_type'])
            return f"{t['name']} ({cat_name} - {type_name})"

        selected = self.select_from_list(templates, "选择要修改的模板",
                                          display_func=display_template)
        if not selected:
            return

        template = selected
        print(f"\n  📝 修改模板: {template['name']}")
        print("  " + "─" * 50)
        print("  (直接回车保留原值)")

        updates = {}

        new_name = self.input_prompt(f"  模板名称", default=template['name'])
        if new_name:
            updates['name'] = new_name

        new_amount_str = self.input_prompt(f"  默认数量", default=str(template['default_amount']))
        if new_amount_str:
            try:
                updates['default_amount'] = float(new_amount_str)
            except ValueError:
                pass

        new_notes = self.input_prompt(f"  默认备注", default=template.get('default_notes', ''))
        if new_notes is not None:
            updates['default_notes'] = new_notes

        print(f"\n  当前周期: {template.get('period', 'on_demand')}")
        print("  [1] 按需使用")
        print("  [2] 每日")
        print("  [3] 每周")
        print("  [4] 每月")
        period_choice = self.input_prompt("  选择周期 (回车不修改)")
        period_map = {'1': 'on_demand', '2': 'daily', '3': 'weekly', '4': 'monthly'}
        if period_choice and period_choice in period_map:
            updates['period'] = period_map[period_choice]

        if updates:
            updated = self.dm.update_template(user_id, template['template_id'], **updates)
            if updated:
                print(f"\n  ✅ 模板更新成功!")
            else:
                print("\n  ❌ 模板更新失败")
        else:
            print("\n  ℹ️  未进行任何修改")

    def _delete_template_wizard(self, user_id, templates):
        if not templates:
            print("\n  📭 暂无模板可删除")
            return

        def display_template(t):
            category_names = self.calc.CATEGORY_NAMES
            cat_name = category_names.get(t['category'], t['category'])
            type_name = self._get_type_name(t['category'], t['activity_type'])
            return f"{t['name']} ({cat_name} - {type_name})"

        selected = self.select_from_list(templates, "选择要删除的模板",
                                          display_func=display_template)
        if not selected:
            return

        if self.confirm_prompt(f"  确定要删除模板「{selected['name']}」吗?",
                                 default=False):
            if self.dm.delete_template(user_id, selected['template_id']):
                print(f"\n  ✅ 模板已删除")
            else:
                print("\n  ❌ 删除失败")

    def view_activity_history(self):
        user_id = self.current_user['user_id']
        print(f"\n  📜 活动记录历史")
        print("  " + "─" * 50)

        print("\n  选择查询范围:")
        print("  [1] 最近20条记录")
        print("  [2] 最近50条记录")
        print("  [3] 今日")
        print("  [4] 本周")
        print("  [5] 本月")
        print("  [6] 全部记录")
        print("  [7] 自定义日期范围")

        choice = self.input_prompt("  请选择", default="1")

        if choice == '1':
            activities = self.dm.list_activities(user_id, limit=20)
            range_name = "最近20条"
        elif choice == '2':
            activities = self.dm.list_activities(user_id, limit=50)
            range_name = "最近50条"
        elif choice == '3':
            activities = self.dm.get_activities_by_period(user_id, 'daily')
            range_name = "今日"
        elif choice == '4':
            activities = self.dm.get_activities_by_period(user_id, 'weekly')
            range_name = "本周"
        elif choice == '5':
            activities = self.dm.get_activities_by_period(user_id, 'monthly')
            range_name = "本月"
        elif choice == '6':
            activities = self.dm.list_activities(user_id)
            range_name = "全部"
        elif choice == '7':
            start = self.input_prompt("  开始日期 (YYYY-MM-DD)", required=True,
                                        validator=lambda x: self._validate_date(x))
            if not start:
                return
            end = self.input_prompt("  结束日期 (YYYY-MM-DD)", required=True,
                                      validator=lambda x: self._validate_date(x))
            if not end:
                return
            activities = self.dm.list_activities(user_id, start_date=start, end_date=end)
            range_name = f"{start} 至 {end}"
        else:
            return

        if not activities:
            print(f"\n  📭 {range_name}范围内暂无活动记录")
            return

        region = self.current_user.get('region', 'national_average')
        category_names = self.calc.CATEGORY_NAMES

        print(f"\n  📋 查询范围: {range_name}  共 {len(activities)} 条记录")
        print("  " + "─" * 90)
        print(f"  {'日期':<12} {'类别':<8} {'类型':<14} {'数量':>8} {'排放(kg)':>10}  {'备注':<20} {'ID':<12}")
        print("  " + "─" * 90)

        total_emission = 0
        for act in activities:
            emission = self.calc.calculate_activity_emission(act, region)
            total_emission += emission
            cat_name = category_names.get(act['category'], act['category'])
            type_name = self._get_type_name(act['category'], act['activity_type'])
            notes = (act.get('notes', '')[:18] + '..') if len(act.get('notes', '')) > 18 else act.get('notes', '')
            print(f"  {act['activity_date']:<12} {cat_name:<8} {type_name:<14} "
                  f"{act['amount']:>8.2f} {emission:>10.2f}  {notes:<20} {act['activity_id']:<12}")

        print("  " + "─" * 90)
        print(f"  {'合计':>46} {total_emission:>10.2f} kg CO₂")

    def delete_activity(self):
        user_id = self.current_user['user_id']
        activities = self.dm.list_activities(user_id, limit=50)

        if not activities:
            print("\n  📭 暂无活动记录可删除")
            return

        region = self.current_user.get('region', 'national_average')
        category_names = self.calc.CATEGORY_NAMES

        print(f"\n  ❌ 删除活动记录  (共显示最近50条)")
        print("  " + "─" * 80)
        for idx, act in enumerate(activities, 1):
            emission = self.calc.calculate_activity_emission(act, region)
            cat_name = category_names.get(act['category'], act['category'])
            type_name = self._get_type_name(act['category'], act['activity_type'])
            print(f"  [{idx:<2}] {act['activity_date']} | {cat_name:<6} {type_name:<10} | "
                  f"{act['amount']:>7} | {emission:>7.2f}kg | {act.get('notes', '')[:15]}")

        while True:
            choice = self.input_prompt("  输入要删除的编号 (0取消)", default="0")
            if not choice or choice == '0':
                print("  已取消删除")
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(activities):
                    target = activities[idx]
                    if self.confirm_prompt(f"  确定删除 ID={target['activity_id']} 的记录吗?"):
                        if self.dm.delete_activity(user_id, target['activity_id']):
                            print("  ✅ 记录已删除")
                    return
            except (ValueError, TypeError):
                pass
            print("  ⚠️  无效的编号")

    def bulk_import_data(self):
        user_id = self.current_user['user_id']
        print("\n  📥 批量导入数据 (支持CSV格式)")
        print("  " + "─" * 50)

        templates = self.importer.list_templates()
        print("\n  可用的数据模板:")
        for idx, t in enumerate(templates, 1):
            print(f"  [{idx}] {t['name']} - {t['description']}")
        print(f"  [{len(templates)+1}] 自动检测格式")

        while True:
            choice = self.input_prompt("  选择模板类型", default=str(len(templates)+1))
            try:
                idx = int(choice)
                if idx == len(templates) + 1:
                    template_key = None
                    break
                if 1 <= idx <= len(templates):
                    template_key = templates[idx - 1]['key']
                    break
            except (ValueError, TypeError):
                pass
            print("  ⚠️  无效的选择")

        file_path = self.input_prompt("  输入CSV文件路径", required=True)
        if not file_path:
            return

        if not os.path.exists(file_path):
            print(f"  ❌ 文件不存在: {file_path}")
            return

        print(f"\n  正在导入 {file_path} ...")
        added_count, added, errors, summary = self.importer.import_csv(user_id, file_path, template_key)

        print(f"\n  {'═' * 60}")
        print(f"  📊 导入结果摘要")
        print(f"  {'═' * 60}")
        print(f"  模板类型: {summary.get('template', '自动检测')}")
        print(f"  总行数: {summary.get('total_rows', 0)}")
        print(f"  {'─' * 60}")
        print(f"  ✅ 成功: {summary.get('success_count', 0)} 条")
        print(f"  ⚠️  跳过: {summary.get('skipped_count', 0)} 条")
        print(f"  ❌ 失败: {summary.get('failed_count', 0)} 条")
        print(f"  {'─' * 60}")

        if summary.get('success_details'):
            print(f"\n  ✅ 成功导入明细 (前{len(summary['success_details'])}条):")
            for item in summary['success_details']:
                region = self.current_user.get('region', 'national_average')
                emission = 0
                if 'activity' in item:
                    emission = self.calc.calculate_activity_emission(item['activity'], region)
                print(f"     - [{item.get('row', '?')}] {item.get('date', '')} "
                      f"{item.get('category_name', '')} - {item.get('type_name', '')}: "
                      f"{item.get('amount', 0)} → {emission:.2f} kg CO₂")

        if summary.get('skipped_details'):
            print(f"\n  ⚠️  跳过明细:")
            for item in summary['skipped_details']:
                print(f"     - [行{item.get('row', '?')}] {item.get('reason', '')}")

        if summary.get('failed_details'):
            print(f"\n  ❌ 失败明细:")
            for item in summary['failed_details']:
                print(f"     - [行{item.get('row', '?')}] {item.get('reason', '')}")

        if added_count > 0:
            print(f"\n  💡 提示: 可在「查看活动历史」中查看所有导入的记录")

    def download_templates(self):
        templates = self.importer.list_templates()
        print("\n  📄 下载数据导入模板")
        print("  " + "─" * 50)

        for idx, t in enumerate(templates, 1):
            print(f"  [{idx}] {t['name']}")
            print(f"       必填列: {', '.join(t['required_columns'])}")

        choice = self.input_prompt("  选择要生成的模板编号", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(templates):
                template_key = templates[idx]['key']
            else:
                print("  ⚠️  无效的选择")
                return
        except (ValueError, TypeError):
            print("  ⚠️  无效的选择")
            return

        default_name = f"import_template_{template_key}.csv"
        output_path = self.input_prompt("  保存路径", default=default_name)
        if not output_path:
            return

        if self.importer.generate_template_csv(template_key, output_path):
            print(f"\n  ✅ 模板已生成: {os.path.abspath(output_path)}")
        else:
            print(f"\n  ❌ 模板生成失败")

    def _get_type_name(self, category, activity_type):
        types = self.dm.get_activity_types(category)
        for t in types:
            if t['key'] == activity_type:
                return t['name']
        return activity_type

    # ==================== 数据分析 ====================

    def menu_analysis(self):
        if not self.current_user:
            print("\n  ⚠️  请先选择用户档案")
            return

        while True:
            self.clear_screen()
            self.banner()
            print(self.viz.section(f'📈 碳排放分析 - {self.current_user["name"]}', 62))
            print("  [1] 综合仪表盘 (总览)")
            print("  [2] 周期排放统计 (日/周/月/年)")
            print("  [3] 排放占比分析 (ASCII饼图)")
            print("  [4] 排放趋势分析 (折线图)")
            print("  [5] 与平均水平对比")
            print("  [6] 目标预测视图")
            print("  [0] 返回主菜单")

            choice = input("\n  请选择操作: ").strip()

            if choice == '1':
                self.show_dashboard()
            elif choice == '2':
                self.period_statistics()
            elif choice == '3':
                self.show_pie_chart()
            elif choice == '4':
                self.show_trend_chart()
            elif choice == '5':
                self.show_benchmark_comparison()
            elif choice == '6':
                self.show_goal_prediction()
            elif choice == '0':
                return
            else:
                print("  ⚠️  无效的选择")

            input("\n  按 Enter 继续...")

    def show_dashboard(self):
        user_id = self.current_user['user_id']
        print("\n  🚀 碳足迹综合仪表盘")
        print(self.viz.header(f'碳排放总览 - {self.current_user["name"]}', 70))

        summary = self.calc.get_user_summary(user_id)
        emissions = summary.get('emissions', {})

        print(f'''
  ┌{'─' * 68}┐
  │  {'📅 今日':<10} {'📆 本周':<12} {'🗓️  本月':<12}                            │
  │  {emissions.get('daily', 0):>7.1f} kg   {emissions.get('weekly', 0):>7.1f} kg   {emissions.get('monthly', 0):>7.1f} kg                      │
  └{'─' * 68}┘
        ''')

        cat_breakdown = summary.get('category_breakdown', [])
        print(self.viz.ascii_pie_chart(cat_breakdown, '📊 本月排放分项占比'))

        print(self.viz.ascii_bar_chart(cat_breakdown, '📊 本月分项排放排名'))

        benchmark = summary.get('benchmark_compare', {})
        print(self.viz.comparison_card(benchmark))

        goals_progress = summary.get('goals_progress', [])
        if goals_progress:
            print(self.viz.section('🎯 减排目标进度'))
            for goal in goals_progress:
                goal_type_name = {
                    'total_emission': '总排放目标',
                    'transport': '交通排放目标',
                    'electricity': '电力排放目标',
                    'food': '饮食排放目标',
                    'shopping': '购物排放目标'
                }.get(goal['goal_type'], goal['goal_type'])
                print(self.viz.progress_card(
                    goal_type_name, goal['current'], goal['target'],
                    unit='kg', width=55
                ))

        suggestions = self.suggester.get_suggestions(user_id, count=3)
        if suggestions:
            print(self.viz.section('💡 个性化减排建议'))
            for idx, s in enumerate(suggestions, 1):
                print(self.suggester.format_suggestion_card(s, idx))

            saving = self.suggester.get_total_potential_saving(suggestions)
            print(f'''
  ┌{'─' * 68}┐
  │  🌱 采纳以上建议，预计每月可减排 {saving['monthly_saving_kg']:>5.0f} kg CO₂                    │
  │     每年可减排 {saving['yearly_saving_kg']:>6.0f} kg，约相当于种植 {saving['yearly_saving_trees']:.0f} 棵树 🌳              │
  └{'─' * 68}┘
            ''')

    def period_statistics(self):
        user_id = self.current_user['user_id']
        print("\n  📊 周期排放统计")
        print("  " + "─" * 50)

        print("""
  选择统计周期:
  [1] 每日 (今天)
  [2] 每周 (本周)
  [3] 每月 (本月)
  [4] 每年 (本年)
  [5] 自定义日期
        """)

        choice = self.input_prompt("  选择周期", default="3")

        if choice == '1':
            period = 'daily'
            ref = date.today()
        elif choice == '2':
            period = 'weekly'
            ref = date.today()
        elif choice == '3':
            period = 'monthly'
            ref = date.today()
        elif choice == '4':
            period = 'yearly'
            ref = date.today()
        elif choice == '5':
            date_str = self.input_prompt("  输入参考日期 (YYYY-MM-DD)", required=True,
                                          validator=lambda x: self._validate_date(x))
            if not date_str:
                return
            ref = datetime.strptime(date_str, '%Y-%m-%d').date()
            p_choice = self.input_prompt("  选择周期 [1日/2周/3月/4年]", default="3")
            period_map = {'1': 'daily', '2': 'weekly', '3': 'monthly', '4': 'yearly'}
            period = period_map.get(p_choice, 'monthly')
        else:
            return

        result = self.calc.calculate_period_emission(user_id, period, ref)

        print(f'''
  📅 统计周期: {result['start_date']} 至 {result['end_date']}
  🔢 活动记录数: {result['activity_count']} 条
  🌫️  碳排放总量: {result['total_emission']:.2f} kg CO₂
        ''')

        print(self.viz.ascii_bar_chart(result['category_breakdown'],
                                         '📊 分类排放统计',
                                         value_key='emission',
                                         label_key='category_name'))

        if result['type_breakdown']:
            print(self.viz.ascii_bar_chart(result['type_breakdown'][:10],
                                             '📋 类型排放TOP10',
                                             value_key='emission',
                                             label_key='type_name'))

    def show_pie_chart(self):
        user_id = self.current_user['user_id']
        print("\n  🥧 排放占比分析")
        print("  " + "─" * 50)

        print("""
  选择统计周期:
  [1] 本周
  [2] 本月  (默认)
  [3] 本年
        """)

        choice = self.input_prompt("  选择周期", default="2")
        period_map = {'1': 'weekly', '2': 'monthly', '3': 'yearly'}
        period = period_map.get(choice, 'monthly')

        result = self.calc.calculate_period_emission(user_id, period)
        period_name = {'daily': '今日', 'weekly': '本周', 'monthly': '本月', 'yearly': '本年'}[period]

        print(self.viz.ascii_pie_chart(result['category_breakdown'],
                                        f'🥧 {period_name}分项排放占比 (总量: {result["total_emission"]:.1f} kg)'))

        if self.confirm_prompt("  是否查看按活动类型的更详细占比?", default=False):
            print(self.viz.ascii_pie_chart(result['type_breakdown'][:12],
                                            f'🥧 {period_name}活动类型排放占比TOP12'))

    def show_trend_chart(self):
        user_id = self.current_user['user_id']
        print("\n  📈 排放趋势分析")
        print("  " + "─" * 50)

        print("""
  选择趋势类型:
  [1] 最近7天 (日)
  [2] 最近6周 (周)
  [3] 最近6个月 (月)  (默认)
  [4] 最近12个月 (月)
        """)

        choice = self.input_prompt("  选择", default="3")

        if choice == '1':
            periods = 7
            period_type = 'daily'
        elif choice == '2':
            periods = 6
            period_type = 'weekly'
        elif choice == '4':
            periods = 12
            period_type = 'monthly'
        else:
            periods = 6
            period_type = 'monthly'

        trend = self.calc.calculate_trend(user_id, periods=periods, period_type=period_type)

        period_name = {'daily': '日度', 'weekly': '周度', 'monthly': '月度'}[period_type]
        title = f'📈 {period_name}排放趋势 (最近{periods}{"天" if period_type=="daily" else "期"})'

        print(self.viz.ascii_line_chart(trend, title))

        print(f"""
  📊 趋势统计:
  ┌{'─' * 50}┐
  │  平均值: {trend['average']:>8.1f} kg    最小值: {trend['min']:>8.1f} kg     │
  │  最大值: {trend['max']:>8.1f} kg    基准值: {trend['benchmark']:>8.1f} kg     │
  └{'─' * 50}┘
        """)

    def show_benchmark_comparison(self):
        user_id = self.current_user['user_id']
        print("\n  ⚖️  与基准水平对比")
        print("  " + "─" * 50)

        period_map = {'1': 'daily', '2': 'weekly', '3': 'monthly'}
        print("""
  选择对比周期:
  [1] 每日
  [2] 每周
  [3] 每月  (默认)
        """)
        choice = self.input_prompt("  选择", default="3")
        period = period_map.get(choice, 'monthly')

        comparison = self.calc.compare_with_benchmark(user_id, period)
        print(self.viz.comparison_card(comparison, width=56))

        china_pct = comparison['vs_china_percent']
        if china_pct > 0:
            print(f"  ⚠️  您的排放比中国平均水平高出 {china_pct:.1f}%，还有减排空间!")
        elif china_pct < 0:
            print(f"  🎉 很好! 您的排放比中国平均水平低 {abs(china_pct):.1f}%")
        else:
            print(f"  📍 您的排放与中国平均水平持平")

    def show_goal_prediction(self):
        user_id = self.current_user['user_id']
        print(f"\n  🎯 目标预测视图")
        print("  " + "─" * 70)

        predictions = self.calc.get_all_goals_prediction(user_id)

        if not predictions:
            print("\n  📭 暂无设置的减排目标，请先在「减排目标」中创建")
            return

        goal_type_names = {
            'total_emission': '总排放',
            'transport': '交通排放',
            'electricity': '电力排放',
            'food': '饮食排放',
            'shopping': '购物排放',
            'heating': '采暖排放'
        }

        print(f"\n  {'目标':<12} {'周期':<6} {'进度':>8} {'当前/目标':>16} "
              f"{'剩余额度':>10} {'日额度':>8} {'预计月底':>10}")
        print("  " + "─" * 90)

        for pred in predictions:
            goal_type = goal_type_names.get(pred['goal_type'], pred['goal_type'])
            period = pred.get('goal_id', '')
            if pred['period_progress'] >= 100:
                progress_str = "已结束"
            else:
                progress_str = f"{pred['days_passed']}/{pred['days_total']}天"

            ratio_str = f"{pred['current']:>7.1f}/{pred['target']:<7.1f}"

            if pred['remaining_quota'] > 0:
                remaining_str = f"{pred['remaining_quota']:>9.1f} kg"
            else:
                remaining_str = f"  已超 {-pred['remaining_quota']:>5.1f} kg"

            if pred['daily_quota'] > 0:
                daily_str = f"{pred['daily_quota']:>6.1f} kg"
            else:
                daily_str = f"  -"

            if pred['will_achieve']:
                projected_str = f"✓ 达标"
                projected_color = "\033[32m"
            else:
                if pred['projected_over'] > pred['target'] * 0.2:
                    projected_str = f"✗ 超{pred['projected_over']:.0f}kg"
                    projected_color = "\033[31m"
                else:
                    projected_str = f"⚠ 超{pred['projected_over']:.0f}kg"
                    projected_color = "\033[33m"

            print(f"  {goal_type:<12} {progress_str:<8} {pred['emission_progress']:>7.1f}% "
                  f"{ratio_str:>16} {remaining_str:>12} {daily_str:>10} "
                  f"{projected_color}{projected_str:>12}\033[0m")

        print("  " + "─" * 90)
        print(f"\n  📊 详细分析:")
        for pred in predictions:
            goal_type = goal_type_names.get(pred['goal_type'], pred['goal_type'])
            print(f"\n  🎯 {goal_type}目标: {pred['risk_description']}")
            print(f"     • 周期进度: {pred['period_progress']:.1f}% ({pred['days_passed']}/{pred['days_total']}天)")
            print(f"     • 排放进度: {pred['emission_progress']:.1f}% ({pred['current']:.1f}/{pred['target']:.1f} kg)")
            print(f"     • 日均排放: {pred['avg_daily_emission']:.3f} kg/天 (基于{pred['historical_periods_used']}个历史周期)")
            print(f"     • 剩余额度: {pred['remaining_quota']:.1f} kg (未来{pred['days_remaining']}天)")
            print(f"     • 每日可用: {pred['daily_quota']:.2f} kg/天")
            print(f"     • 预计月底: {pred['projected_total']:.1f} kg (目标: {pred['target']:.1f} kg)")

            if not pred['will_achieve'] and pred['projected_over'] > 0:
                need_reduce_daily = max(0, pred['avg_daily_emission'] - pred['daily_quota'])
                if need_reduce_daily > 0:
                    print(f"     • 💡 建议: 每天需再减少 {need_reduce_daily:.2f} kg 排放才能达标")

    # ==================== 目标管理 ====================

    def menu_goals(self):
        if not self.current_user:
            print("\n  ⚠️  请先选择用户档案")
            return

        while True:
            self.clear_screen()
            self.banner()
            print(self.viz.section(f'🎯 减排目标管理 - {self.current_user["name"]}', 62))
            print("  [1] 查看目标及完成进度")
            print("  [2] 创建新的减排目标")
            print("  [3] 标记目标已完成")
            print("  [4] 删除目标")
            print("  [0] 返回主菜单")

            choice = input("\n  请选择操作: ").strip()

            if choice == '1':
                self.view_goal_progress()
            elif choice == '2':
                self.create_goal()
            elif choice == '3':
                self.mark_goal_achieved()
            elif choice == '4':
                self.delete_goal()
            elif choice == '0':
                return
            else:
                print("  ⚠️  无效的选择")

            input("\n  按 Enter 继续...")

    def view_goal_progress(self):
        user_id = self.current_user['user_id']
        print("\n  📊 减排目标进度")
        print("  " + "─" * 50)

        active_goals = self.dm.list_goals(user_id, active_only=True)
        all_goals = self.dm.list_goals(user_id, active_only=False)
        achieved_goals = [g for g in all_goals if g.get('achieved_at')]

        if not all_goals:
            print("  📭 暂无减排目标，快去创建一个吧!")
            return

        if active_goals:
            print(f"\n  🎯 进行中的目标 ({len(active_goals)} 个):")
            progress = self.calc.get_all_goals_progress(user_id)

            goal_type_names = {
                'total_emission': '总排放量',
                'transport': '交通排放',
                'electricity': '电力排放',
                'food': '饮食排放',
                'shopping': '购物排放',
                'heating': '采暖排放'
            }

            for idx, (goal, prog) in enumerate(zip(active_goals, progress), 1):
                gt = goal_type_names.get(goal['goal_type'], goal['goal_type'])
                period_name = {'daily': '日', 'weekly': '周', 'monthly': '月', 'yearly': '年'}[goal.get('period', 'monthly')]
                title = f"{period_name}度{gt}"
                if goal.get('description'):
                    title += f" - {goal['description']}"
                print(f"\n  {idx}. {title}")
                print(self.viz.progress_card(
                    '',
                    prog['current'], goal['target'],
                    unit='kg CO₂', width=58
                ).replace('│  │ │', '│    │').replace('┌─  ┐', '┌' + '─' * 56 + '┐'))

        if achieved_goals:
            print(f"\n  ✅ 已完成的目标 ({len(achieved_goals)} 个):")
            for goal in achieved_goals:
                achieved_at = goal.get('achieved_at', '')[:10]
                desc = goal.get('description', '') or goal['goal_type']
                print(f"     ✓ {desc} - 达成于 {achieved_at}")

    def create_goal(self):
        user_id = self.current_user['user_id']
        print("\n  ➕ 创建减排目标")
        print("  " + "─" * 50)

        print("""
  选择目标类型:
  [1] 总排放量
  [2] 交通排放量
  [3] 电力排放量
  [4] 饮食排放量
  [5] 购物排放量
  [6] 采暖排放量
        """)

        type_map = {
            '1': 'total_emission', '2': 'transport', '3': 'electricity',
            '4': 'food', '5': 'shopping', '6': 'heating'
        }
        type_choice = self.input_prompt("  选择目标类型", default="1")
        goal_type = type_map.get(type_choice, 'total_emission')

        print("""
  选择目标周期:
  [1] 日
  [2] 周
  [3] 月  (默认)
  [4] 年
        """)
        period_map = {'1': 'daily', '2': 'weekly', '3': 'monthly', '4': 'yearly'}
        p_choice = self.input_prompt("  选择周期", default="3")
        period = period_map.get(p_choice, 'monthly')

        benchmarks = self.dm.get_benchmarks()
        benchmark_key = f'china_{period}_per_capita'
        benchmark_value = benchmarks.get(benchmark_key, 500)

        current_result = self.calc.calculate_period_emission(user_id, period)
        current_value = 0
        if goal_type == 'total_emission':
            current_value = current_result['total_emission']
        else:
            for cat in current_result['category_breakdown']:
                if cat['category'] == goal_type:
                    current_value = cat['emission']
                    break

        suggested_target = 0
        if current_value > 0:
            suggested_target = round(current_value * 0.8, 1)
        elif benchmark_value > 0:
            suggested_target = round(benchmark_value * 0.9, 1)

        print(f"""
  💡 参考信息:
  - 本{period}当前排放: {current_value:.1f} kg CO₂
  - 中国人均{period}排放: {benchmark_value:.1f} kg CO₂
  - 建议目标值 (降低20%): {suggested_target:.1f} kg CO₂
        """)

        while True:
            target_str = self.input_prompt(f"  设定目标值 (kg CO₂)", default=str(suggested_target),
                                            required=True)
            if target_str is None:
                return
            try:
                target_value = float(target_str)
                if target_value <= 0:
                    print("  ⚠️  目标值必须大于0")
                    continue
                break
            except ValueError:
                print("  ⚠️  请输入有效的数字")

        description = self.input_prompt("  目标描述 (可选)")

        start_date = self.input_prompt("  开始日期 (YYYY-MM-DD)",
                                        default=date.today().isoformat(),
                                        validator=lambda x: self._validate_date(x))

        goal = self.dm.set_goal(user_id, goal_type, target_value, period,
                                start_date, description or '')
        if goal:
            print(f"\n  ✅ 减排目标创建成功! 目标ID: {goal['goal_id']}")

    def mark_goal_achieved(self):
        user_id = self.current_user['user_id']
        goals = self.dm.list_goals(user_id, active_only=True)
        if not goals:
            print("\n  📭 没有进行中的目标")
            return

        print(f"\n  ✅ 标记目标完成 (共 {len(goals)} 个进行中的目标)")
        for idx, g in enumerate(goals, 1):
            desc = g.get('description', '') or g['goal_type']
            period = g.get('period', 'monthly')
            print(f"  [{idx}] {desc} - {period}目标: {g['target_value']} kg")

        choice = self.input_prompt("  选择编号", required=True)
        if not choice:
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(goals):
                goal_id = goals[idx]['goal_id']
                if self.dm.mark_goal_achieved(user_id, goal_id):
                    print("  ✅ 目标已标记为完成!")
        except (ValueError, TypeError):
            print("  ⚠️  无效的选择")

    def delete_goal(self):
        user_id = self.current_user['user_id']
        all_goals = self.dm.list_goals(user_id, active_only=False)
        if not all_goals:
            print("\n  📭 没有目标可删除")
            return

        print(f"\n  ❌ 删除目标 (共 {len(all_goals)} 个)")
        for idx, g in enumerate(all_goals, 1):
            status = "✓ 已完成" if g.get('achieved_at') else "⏳ 进行中"
            desc = g.get('description', '') or g['goal_type']
            print(f"  [{idx}] {desc} [{status}]")

        choice = self.input_prompt("  选择要删除的编号", default="0")
        if not choice or choice == '0':
            print("  已取消")
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_goals):
                goal_id = all_goals[idx]['goal_id']
                if self.confirm_prompt("  确定删除此目标吗?", default=False):
                    if self.dm.delete_goal(user_id, goal_id):
                        print("  ✅ 目标已删除")
        except (ValueError, TypeError):
            print("  ⚠️  无效的选择")

    # ==================== 减排建议 ====================

    def menu_suggestions(self):
        if not self.current_user:
            print("\n  ⚠️  请先选择用户档案")
            return

        user_id = self.current_user['user_id']
        self.clear_screen()
        self.banner()
        print(self.viz.section(f'💡 个性化减排建议 - {self.current_user["name"]}', 62))

        print("\n  🔍 正在分析您的排放数据...")
        suggestions = self.suggester.get_suggestions(user_id, count=3)

        if not suggestions:
            print("\n  📭 暂无建议，请先记录更多活动数据")
            input("\n  按 Enter 继续...")
            return

        print(f"\n  📋 为您匹配了 {len(suggestions)} 条最佳减排建议:\n")
        for idx, s in enumerate(suggestions, 1):
            print(self.suggester.format_suggestion_card(s, idx))

        saving = self.suggester.get_total_potential_saving(suggestions)
        print(f'''
  ╔{'═' * 70}╗
  ║  🌱 减排潜力总结                                                     ║
  ╠{'═' * 70}╣
  ║                                                                      ║
  ║    采纳以上建议预计可实现:                                            ║
  ║                                                                      ║
  ║      · 每月减排: {saving['monthly_saving_kg']:>7.1f} kg CO₂                                       ║
  ║      · 每年减排: {saving['yearly_saving_kg']:>7.1f} kg CO₂                                        ║
  ║      · 相当于种植: {saving['yearly_saving_trees']:>5.0f} 棵树 🌳                                        ║
  ║                                                                      ║
  ╚{'═' * 70}╝
        ''')

        input("\n  按 Enter 返回主菜单...")

    # ==================== 导出报告 ====================

    def menu_export(self):
        if not self.current_user:
            print("\n  ⚠️  请先选择用户档案")
            return

        while True:
            self.clear_screen()
            self.banner()
            print(self.viz.section(f'📤 报告导出 - {self.current_user["name"]}', 62))
            print("  [1] 导出活动明细 (CSV)")
            print("  [2] 导出汇总统计 (CSV)")
            print("  [3] 导出完整HTML报告 (推荐)")
            print("  [0] 返回主菜单")

            choice = input("\n  请选择操作: ").strip()

            if choice == '1':
                self.export_activities_csv()
            elif choice == '2':
                self.export_summary_csv()
            elif choice == '3':
                self.export_html_report()
            elif choice == '0':
                return
            else:
                print("  ⚠️  无效的选择")

            input("\n  按 Enter 继续...")

    def export_activities_csv(self):
        user_id = self.current_user['user_id']
        print("\n  📤 导出活动明细 CSV")
        print("  " + "─" * 50)

        print("""
  选择导出范围:
  [1] 全部记录
  [2] 本月
  [3] 本周
  [4] 自定义日期范围
        """)

        choice = self.input_prompt("  选择", default="1")
        start_date = end_date = None
        period = 'all'

        if choice == '2':
            period = 'monthly'
        elif choice == '3':
            period = 'weekly'
        elif choice == '4':
            start_date = self.input_prompt("  开始日期 (YYYY-MM-DD)", required=True,
                                            validator=lambda x: self._validate_date(x))
            if not start_date:
                return
            end_date = self.input_prompt("  结束日期 (YYYY-MM-DD)", required=True,
                                          validator=lambda x: self._validate_date(x))
            if not end_date:
                return

        default_name = f"carbon_activities_{self.current_user['user_id']}_{date.today().isoformat()}.csv"
        output_path = self.input_prompt("  保存文件路径", default=default_name)
        if not output_path:
            return

        success = self.exporter.export_csv(user_id, output_path, period, start_date, end_date)
        if success:
            print(f"\n  ✅ 导出成功! 文件: {os.path.abspath(output_path)}")
        else:
            print(f"\n  ❌ 导出失败")

    def export_summary_csv(self):
        user_id = self.current_user['user_id']
        print("\n  📤 导出汇总统计 CSV")

        default_name = f"carbon_summary_{self.current_user['user_id']}_{date.today().isoformat()}.csv"
        output_path = self.input_prompt("  保存文件路径", default=default_name)
        if not output_path:
            return

        success = self.exporter.export_summary_csv(user_id, output_path)
        if success:
            print(f"\n  ✅ 导出成功! 文件: {os.path.abspath(output_path)}")
        else:
            print(f"\n  ❌ 导出失败")

    def export_html_report(self):
        user_id = self.current_user['user_id']
        print("\n  📤 导出完整HTML报告")
        print("  ℹ️  包含图表、建议、目标进度等全部分析内容")

        default_name = f"carbon_report_{self.current_user['user_id']}_{date.today().isoformat()}.html"
        output_path = self.input_prompt("  保存文件路径", default=default_name)
        if not output_path:
            return

        success = self.exporter.export_html(user_id, output_path)
        if success:
            abs_path = os.path.abspath(output_path)
            print(f"\n  ✅ 报告生成成功! 文件: {abs_path}")
            if self.confirm_prompt("  是否在浏览器中打开报告?", default=True):
                try:
                    if os.name == 'nt':
                        os.startfile(abs_path)
                    elif sys.platform == 'darwin':
                        os.system(f'open "{abs_path}"')
                    else:
                        os.system(f'xdg-open "{abs_path}"')
                    print("  🖥️  已在浏览器中打开")
                except Exception:
                    print(f"  请手动打开文件: {abs_path}")
        else:
            print(f"\n  ❌ 报告生成失败")

    # ==================== 主菜单 ====================

    def main_menu(self):
        while True:
            self.clear_screen()
            self.banner()

            if self.current_user:
                print(f"  👤 当前用户: {self.current_user['name']} | ID: {self.current_user['user_id']}\n")
            else:
                print("  ⚠️  未选择用户 请先创建或选择用户档案\n")

            print(self.viz.section('🏠 主菜单', 62))
            print("  [1] 👥  用户档案管理")
            print("  [2] 📊  活动记录管理")
            print("  [3] 📈  碳排放分析")
            print("  [4] 🎯  减排目标管理")
            print("  [5] 💡  个性化减排建议")
            print("  [6] 📤  报告导出")
            print("  [7] 🚀  快速演示 (生成示例数据)")
            print("  [0] 👋  退出程序")

            choice = input("\n  请选择操作: ").strip()

            if choice == '1':
                self.menu_user_management()
            elif choice == '2':
                self.menu_activity_management()
            elif choice == '3':
                self.menu_analysis()
            elif choice == '4':
                self.menu_goals()
            elif choice == '5':
                self.menu_suggestions()
            elif choice == '6':
                self.menu_export()
            elif choice == '7':
                self.run_demo()
            elif choice == '0' or choice.lower() == 'q':
                print("\n  👋 感谢使用碳足迹追踪工具!")
                print("  🌱 践行低碳生活，保护地球家园 🌍\n")
                break
            else:
                print("  ⚠️  无效的选择，请输入菜单编号")
                input("\n  按 Enter 继续...")

    def run_demo(self):
        print("\n  🚀 快速演示模式")
        print("  " + "─" * 50)

        demo_user = None
        users = self.dm.list_users()
        if users:
            demo_user = self.dm.get_user(users[0]['user_id'])
            self.current_user = demo_user
            print(f"  ℹ️  使用已有用户: {demo_user['name']}")
        else:
            print("  📝 创建演示用户...")
            demo_user = self.dm.create_user('演示用户', 'east_china', 3, '自动生成的演示账号')
            self.current_user = demo_user
            print(f"  ✅ 用户已创建: {demo_user['name']}")

            print("\n  📊 正在生成示例活动数据...")

            from datetime import date, timedelta
            import random

            user_id = demo_user['user_id']
            today = date.today()

            for day_offset in range(30):
                d = today - timedelta(days=day_offset)
                date_str = d.isoformat()

                transport_options = [
                    ('car_gasoline', random.uniform(10, 60)),
                    ('subway', random.uniform(5, 25)),
                    ('bus', random.uniform(3, 15)),
                    ('bicycle', random.uniform(2, 10)),
                    ('walking', random.uniform(0.5, 3)),
                    ('ride_share', random.uniform(5, 20)),
                ]
                selected = random.sample(transport_options, k=random.randint(1, 3))
                for act_type, amount in selected:
                    self.dm.add_activity(user_id, 'transport', act_type, amount, date_str, '演示数据')

                self.dm.add_activity(user_id, 'electricity', 'grid_electricity',
                                      random.uniform(5, 15), date_str, '演示数据')

                food_options = ['beef', 'pork', 'chicken', 'fish', 'rice',
                                'vegetables', 'fruits', 'egg', 'dairy', 'bread', 'legumes']
                selected_foods = random.sample(food_options, k=random.randint(3, 6))
                for food in selected_foods:
                    self.dm.add_activity(user_id, 'food', food,
                                          random.randint(1, 3), date_str, '演示数据')

                if random.random() < 0.3:
                    shop_types = ['clothing', 'household', 'books', 'beauty', 'digital_service']
                    self.dm.add_activity(user_id, 'shopping',
                                          random.choice(shop_types),
                                          random.randint(1, 2), date_str, '演示数据')

                if day_offset % 10 == 0:
                    self.dm.add_activity(user_id, 'waste', 'general_waste',
                                          random.uniform(1, 3), date_str, '演示数据')

            print("  ✅ 示例数据生成完成 (约30天的数据)")

            print("\n  🎯 创建减排目标...")
            self.dm.set_goal(user_id, 'total_emission', 450, 'monthly',
                              today.isoformat(), '月度总排放目标')
            self.dm.set_goal(user_id, 'transport', 150, 'monthly',
                              today.isoformat(), '月度交通排放目标')
            print("  ✅ 目标创建完成")

        print("\n  🎬 演示数据准备完毕，现在为您展示...")
        input("\n  按 Enter 查看综合仪表盘...")

        self.clear_screen()
        self.banner()
        self.show_dashboard()

        print("\n  📌 演示完成!")
        print("  您可以通过主菜单进一步探索各个功能模块")

    def check_first_run(self):
        users = self.dm.list_users()
        if not users:
            print("\n  🎉 欢迎使用碳足迹追踪工具!")
            print("  检测到您是首次使用，让我们开始创建您的第一个档案吧~")
            if self.confirm_prompt("  是否现在创建用户档案?", default=True):
                self.create_user()
            if self.confirm_prompt("\n  是否快速生成演示数据来体验功能?", default=True):
                self.run_demo()


def main():
    try:
        cli = CarbonTrackerCLI()
        cli.check_first_run()
        cli.main_menu()
    except KeyboardInterrupt:
        print("\n\n  👋 程序已退出")
        sys.exit(0)
    except Exception as e:
        print(f"\n  ❌ 程序出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
