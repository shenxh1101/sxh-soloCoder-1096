import csv
import os
from datetime import date, datetime
from typing import List, Dict, Optional
from pathlib import Path

from .data_manager import DataManager
from .calculator import CarbonCalculator
from .suggester import Suggester


class ReportExporter:
    def __init__(self, data_manager: DataManager, calculator: CarbonCalculator,
                 suggester: Suggester = None):
        self.dm = data_manager
        self.calc = calculator
        self.suggester = suggester

    def export_csv(self, user_id: str, output_path: str,
                   period: str = 'all', start_date: str = None,
                   end_date: str = None) -> bool:
        user = self.dm.get_user(user_id)
        if not user:
            return False

        if period == 'all':
            activities = self.dm.list_activities(user_id, start_date, end_date)
        else:
            activities = self.dm.get_activities_by_period(user_id, period)

        try:
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    '活动ID', '类别', '类别名称', '活动类型', '活动名称',
                    '数量', '单位', '碳排放(kg CO2)', '活动日期', '备注', '创建时间'
                ])

                region = user.get('region', 'national_average')
                for act in activities:
                    emission = self.calc.calculate_activity_emission(act, region)
                    cat_name = self.calc.CATEGORY_NAMES.get(act['category'], act['category'])
                    type_name = self._get_type_name(act['category'], act['activity_type'])
                    unit = self._get_unit(act['category'], act['activity_type'])

                    writer.writerow([
                        act['activity_id'],
                        act['category'],
                        cat_name,
                        act['activity_type'],
                        type_name,
                        act['amount'],
                        unit,
                        emission,
                        act['activity_date'],
                        act.get('notes', ''),
                        act.get('created_at', '')
                    ])
            return True
        except Exception:
            return False

    def export_summary_csv(self, user_id: str, output_path: str,
                            reference_date: date = None) -> bool:
        user = self.dm.get_user(user_id)
        if not user:
            return False

        if reference_date is None:
            reference_date = date.today()

        daily = self.calc.calculate_period_emission(user_id, 'daily', reference_date)
        weekly = self.calc.calculate_period_emission(user_id, 'weekly', reference_date)
        monthly = self.calc.calculate_period_emission(user_id, 'monthly', reference_date)
        yearly = self.calc.calculate_period_emission(user_id, 'yearly', reference_date)
        comparison = self.calc.compare_with_benchmark(user_id, 'monthly', reference_date)

        try:
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)

                writer.writerow(['=== 用户信息 ==='])
                writer.writerow(['用户ID', user['user_id']])
                writer.writerow(['姓名', user['name']])
                writer.writerow(['地区', user.get('region', 'national_average')])
                writer.writerow(['家庭人数', user.get('household_size', 1)])
                writer.writerow([])

                writer.writerow(['=== 排放汇总 ==='])
                writer.writerow(['统计周期', '开始日期', '结束日期', '总排放(kg CO2)', '活动数量'])
                for period_data in [daily, weekly, monthly, yearly]:
                    writer.writerow([
                        self._period_name(period_data['period']),
                        period_data['start_date'],
                        period_data['end_date'],
                        period_data['total_emission'],
                        period_data['activity_count']
                    ])
                writer.writerow([])

                writer.writerow(['=== 月度分项排放 ==='])
                writer.writerow(['类别', '类别名称', '排放(kg CO2)', '占比(%)'])
                for cat in monthly['category_breakdown']:
                    writer.writerow([
                        cat['category'],
                        cat['category_name'],
                        cat['emission'],
                        cat['percentage']
                    ])
                writer.writerow([])

                writer.writerow(['=== 与基准对比 ==='])
                writer.writerow(['对比项', '排放(kg CO2)', '差异(%)'])
                writer.writerow(['您的月度排放', comparison['user_emission'], '—'])
                writer.writerow(['中国平均', comparison['china_average'], comparison['vs_china_percent']])
                writer.writerow(['全球平均', comparison['global_average'], comparison['vs_global_percent']])
                writer.writerow(['欧盟平均', comparison['eu_average'], comparison['vs_eu_percent']])
                writer.writerow([])

                goals = self.calc.get_all_goals_progress(user_id, reference_date)
                if goals:
                    writer.writerow(['=== 目标进度 ==='])
                    writer.writerow(['目标ID', '目标类型', '目标值', '当前值', '完成度(%)', '是否达标'])
                    for g in goals:
                        writer.writerow([
                            g['goal_id'],
                            g['goal_type'],
                            g['target'],
                            g['current'],
                            g['progress_percent'],
                            '是' if g['achieved'] else '否'
                        ])

            return True
        except Exception:
            return False

    def export_html(self, user_id: str, output_path: str,
                    reference_date: date = None) -> bool:
        user = self.dm.get_user(user_id)
        if not user:
            return False

        if reference_date is None:
            reference_date = date.today()

        summary = self.calc.get_user_summary(user_id)
        suggestions = None
        if self.suggester:
            suggestions = self.suggester.get_suggestions(user_id, count=3)
            saving_summary = self.suggester.get_total_potential_saving(suggestions)
        else:
            saving_summary = None

        html_content = self._build_html(user, summary, suggestions, saving_summary)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return True
        except Exception:
            return False

    def _build_html(self, user: Dict, summary: Dict,
                    suggestions: List[Dict], saving_summary: Dict) -> str:
        css = '''
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                             "Microsoft YaHei", sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 30px 20px;
                color: #2c3e50;
            }
            .container {
                max-width: 960px;
                margin: 0 auto;
                background: #fff;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #00b894 0%, #00cec9 100%);
                color: white;
                padding: 36px 40px;
            }
            .header h1 { font-size: 28px; margin-bottom: 8px; }
            .header .subtitle { opacity: 0.9; font-size: 15px; }
            .content { padding: 32px 40px; }
            .section { margin-bottom: 32px; }
            .section-title {
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 16px;
                padding-bottom: 10px;
                border-bottom: 2px solid #ecf0f1;
                color: #2c3e50;
            }
            .section-title::before {
                content: "🌿 ";
            }
            .grid-3 {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }
            .stat-card {
                background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
                border-radius: 12px;
                padding: 20px;
                text-align: center;
            }
            .stat-card.highlight {
                background: linear-gradient(135deg, #00b894 0%, #00cec9 100%);
                color: white;
            }
            .stat-card .label { font-size: 13px; opacity: 0.8; margin-bottom: 6px; }
            .stat-card .value { font-size: 28px; font-weight: 700; }
            .stat-card .unit { font-size: 14px; opacity: 0.8; margin-left: 4px; }

            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }
            th {
                background: #f0f4f8;
                padding: 14px 16px;
                text-align: left;
                font-weight: 600;
                font-size: 14px;
                color: #34495e;
            }
            td {
                padding: 12px 16px;
                border-bottom: 1px solid #ecf0f1;
                font-size: 14px;
            }
            tr:last-child td { border-bottom: none; }
            .bar-cell {
                width: 180px;
            }
            .bar-bg {
                background: #ecf0f1;
                height: 10px;
                border-radius: 5px;
                overflow: hidden;
            }
            .bar-fill {
                height: 100%;
                background: linear-gradient(90deg, #00b894, #00cec9);
                border-radius: 5px;
            }

            .suggestion-card {
                background: #f8faf9;
                border-left: 4px solid #00b894;
                padding: 18px 22px;
                margin-bottom: 14px;
                border-radius: 0 10px 10px 0;
            }
            .suggestion-title {
                font-weight: 600;
                font-size: 16px;
                margin-bottom: 8px;
                color: #2c3e50;
            }
            .suggestion-meta {
                font-size: 12px;
                color: #7f8c8d;
                margin-bottom: 8px;
            }
            .suggestion-meta span {
                background: #e8f8f4;
                padding: 3px 10px;
                border-radius: 12px;
                margin-right: 8px;
                color: #00b894;
                font-weight: 500;
            }
            .suggestion-desc { color: #555; font-size: 14px; line-height: 1.6; }
            .saving-badge {
                display: inline-block;
                background: linear-gradient(135deg, #fdcb6e 0%, #f39c12 100%);
                color: white;
                padding: 3px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                margin-left: 8px;
            }
            .goal-progress {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .goal-bar-bg {
                flex: 1;
                height: 14px;
                background: #ecf0f1;
                border-radius: 7px;
                overflow: hidden;
            }
            .goal-bar-fill {
                height: 100%;
                border-radius: 7px;
                transition: width 0.3s ease;
            }
            .goal-bar-fill.good { background: linear-gradient(90deg, #00b894, #00cec9); }
            .goal-bar-fill.warn { background: linear-gradient(90deg, #fdcb6e, #f39c12); }
            .goal-bar-fill.bad { background: linear-gradient(90deg, #e17055, #d63031); }

            .comparison-row {
                display: flex;
                align-items: center;
                margin-bottom: 14px;
                gap: 14px;
            }
            .comp-label { width: 90px; font-size: 14px; color: #555; }
            .comp-bar-wrap { flex: 1; }
            .comp-bar {
                height: 24px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: flex-end;
                padding-right: 10px;
                color: white;
                font-size: 13px;
                font-weight: 600;
            }
            .comp-bar.user { background: linear-gradient(90deg, #6c5ce7, #a29bfe); }
            .comp-bar.china { background: linear-gradient(90deg, #0984e3, #74b9ff); }
            .comp-bar.global { background: linear-gradient(90deg, #00b894, #55efc4); }
            .comp-bar.eu { background: linear-gradient(90deg, #fdcb6e, #ffeaa7); color: #2c3e50; }
            .comp-value { width: 80px; text-align: right; font-weight: 600; }

            .footer {
                text-align: center;
                padding: 24px 40px;
                background: #f8faf9;
                color: #7f8c8d;
                font-size: 13px;
            }
            .saving-summary {
                background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%);
                border-radius: 12px;
                padding: 18px 24px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-around;
                text-align: center;
            }
            .saving-item .num { font-size: 24px; font-weight: 700; color: #e17055; }
            .saving-item .lbl { font-size: 12px; color: #7f6000; margin-top: 4px; }

            .tips-list {
                list-style: none;
                padding: 0;
                margin-top: 10px;
            }
            .tips-list li {
                padding: 4px 0 4px 20px;
                position: relative;
                font-size: 13px;
                color: #666;
            }
            .tips-list li::before {
                content: "💡";
                position: absolute;
                left: 0;
            }
        </style>
        '''

        emissions = summary.get('emissions', {})
        cat_breakdown = summary.get('category_breakdown', [])
        benchmark = summary.get('benchmark_compare', {})
        goals_progress = summary.get('goals_progress', [])
        user_info = summary.get('user', {})

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>个人碳足迹报告 - {user['name']}</title>
    {css}
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🌍 个人碳足迹分析报告</h1>
        <div class="subtitle">
            {user['name']} | 地区: {user_info.get('region', '全国平均')} |
            生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
        </div>
    </div>
    <div class="content">
        <div class="section">
            <div class="section-title">排放概览</div>
            <div class="grid-3">
                <div class="stat-card">
                    <div class="label">今日排放</div>
                    <div class="value">{emissions.get('daily', 0):.1f}<span class="unit">kg CO₂</span></div>
                </div>
                <div class="stat-card">
                    <div class="label">本周排放</div>
                    <div class="value">{emissions.get('weekly', 0):.1f}<span class="unit">kg CO₂</span></div>
                </div>
                <div class="stat-card highlight">
                    <div class="label">本月排放</div>
                    <div class="value">{emissions.get('monthly', 0):.1f}<span class="unit">kg CO₂</span></div>
                </div>
            </div>
        </div>
        '''

        if saving_summary:
            html += f'''
        <div class="section">
            <div class="section-title">减排潜力</div>
            <div class="saving-summary">
                <div class="saving-item">
                    <div class="num">{saving_summary['monthly_saving_kg']:.0f} kg</div>
                    <div class="lbl">预计月减排</div>
                </div>
                <div class="saving-item">
                    <div class="num">{saving_summary['yearly_saving_kg']:.0f} kg</div>
                    <div class="lbl">预计年减排</div>
                </div>
                <div class="saving-item">
                    <div class="num">{saving_summary['yearly_saving_trees']:.0f} 棵</div>
                    <div class="lbl">相当于种树</div>
                </div>
            </div>
        </div>
            '''

        html += '''
        <div class="section">
            <div class="section-title">月度分项排放</div>
            <table>
                <thead>
                    <tr>
                        <th>类别</th>
                        <th class="bar-cell">排放分布</th>
                        <th>排放量</th>
                        <th>占比</th>
                    </tr>
                </thead>
                <tbody>
        '''

        if cat_breakdown:
            max_cat_emission = max(c['emission'] for c in cat_breakdown) or 1
            for cat in cat_breakdown:
                pct = (cat['emission'] / max_cat_emission * 100) if max_cat_emission > 0 else 0
                html += f'''
                    <tr>
                        <td>{cat['category_name']}</td>
                        <td class="bar-cell">
                            <div class="bar-bg"><div class="bar-fill" style="width:{pct:.0f}%"></div></div>
                        </td>
                        <td>{cat['emission']:.2f} kg</td>
                        <td>{cat['percentage']:.1f}%</td>
                    </tr>
                '''

        html += '''
                </tbody>
            </table>
        </div>

        <div class="section">
            <div class="section-title">与平均水平对比</div>
        '''

        comp_data = [
            ('您的排放', 'user', benchmark.get('user_emission', 0), ''),
            ('中国平均', 'china', benchmark.get('china_average', 0),
             f"{benchmark.get('vs_china_percent', 0):+.1f}%"),
            ('全球平均', 'global', benchmark.get('global_average', 0),
             f"{benchmark.get('vs_global_percent', 0):+.1f}%"),
            ('欧盟平均', 'eu', benchmark.get('eu_average', 0),
             f"{benchmark.get('vs_eu_percent', 0):+.1f}%")
        ]

        max_comp = max(v for _, _, v, _ in comp_data) or 1
        for label, cls, value, diff in comp_data:
            w = (value / max_comp * 100) if max_comp > 0 else 0
            html += f'''
            <div class="comparison-row">
                <div class="comp-label">{label}</div>
                <div class="comp-bar-wrap">
                    <div class="comp-bar {cls}" style="width:{max(10, w):.0f}%">
                        {diff if diff else ''}
                    </div>
                </div>
                <div class="comp-value">{value:.1f} kg</div>
            </div>
            '''

        html += '''
        </div>
        '''

        if goals_progress:
            html += '''
        <div class="section">
            <div class="section-title">目标完成进度</div>
            <table>
                <thead>
                    <tr>
                        <th>目标</th>
                        <th>进度</th>
                        <th>当前/目标</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
            '''

            for goal in goals_progress:
                achieved = goal.get('achieved', False)
                current = goal['current']
                target = goal['target']
                overage = goal.get('overage', 0)

                if achieved:
                    bar_cls = 'good'
                    if target > 0:
                        remaining_pct = ((target - current) / target) * 100
                        status = f'✅ 已达标 (还剩 {goal.get("remaining", 0):.1f} kg 额度)'
                        bar_pct = min(100, remaining_pct)
                    else:
                        status = '✅ 已达标'
                        bar_pct = 100
                elif overage <= target * 0.1:
                    bar_cls = 'warn'
                    over_pct = min(20, (overage / target) * 100)
                    status = f'⚠️ 轻微超标 (+{overage:.1f} kg)'
                    bar_pct = 100 + over_pct
                else:
                    bar_cls = 'bad'
                    over_pct = min(30, (overage / target) * 100)
                    status = f'❌ 严重超标 (+{overage:.1f} kg)'
                    bar_pct = 100 + over_pct

                pct = max(10, min(130, bar_pct))
                display_pct = max(0, min(100, goal['progress_percent']))

                goal_type_name = {
                    'total_emission': '总排放',
                    'transport': '交通排放',
                    'electricity': '电力排放',
                    'food': '饮食排放',
                    'shopping': '购物排放'
                }.get(goal['goal_type'], goal['goal_type'])

                html += f'''
                    <tr>
                        <td>{goal_type_name}</td>
                        <td style="width:300px">
                            <div class="goal-progress">
                                <div class="goal-bar-bg">
                                    <div class="goal-bar-fill {bar_cls}" style="width:{pct:.0f}%"></div>
                                </div>
                                <span style="font-size:13px;font-weight:600;width:50px">{display_pct:.0f}%</span>
                            </div>
                        </td>
                        <td>{goal['current']:.1f} / {goal['target']:.1f} kg</td>
                        <td>{status}</td>
                    </tr>
                '''

            html += '''
                </tbody>
            </table>
        </div>
            '''

        if suggestions:
            html += '''
        <div class="section">
            <div class="section-title">个性化减排建议</div>
            '''

            for idx, s in enumerate(suggestions, 1):
                diff_name = s.get('difficulty_name', '')
                impact_name = s.get('impact_name', '')
                saving = s.get('calculated_saving_kg', 0)
                impact_pct = s.get('impact_percent', 0)

                html += f'''
            <div class="suggestion-card">
                <div class="suggestion-title">
                    建议{idx}: {s.get('title', '')}
                    <span class="saving-badge">月省 {saving:.1f} kg ({impact_pct:.1f}%)</span>
                </div>
                <div class="suggestion-meta">
                    <span>难度: {diff_name}</span>
                    <span>效果: {impact_name}</span>
                </div>
                <div class="suggestion-desc">{s.get('description', '')}</div>
                '''

                tips = s.get('tips', [])
                if tips:
                    html += '<ul class="tips-list">'
                    for tip in tips:
                        html += f'<li>{tip}</li>'
                    html += '</ul>'

                html += '</div>'

            html += '''
        </div>
            '''

        html += f'''
    </div>
    <div class="footer">
        🌱 低碳生活，从我做起 | 报告生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</div>
</body>
</html>
        '''

        return html

    def _period_name(self, period: str) -> str:
        names = {
            'daily': '每日',
            'weekly': '每周',
            'monthly': '每月',
            'yearly': '每年'
        }
        return names.get(period, period)

    def _get_type_name(self, category: str, activity_type: str) -> str:
        types = self.dm.get_activity_types(category)
        for t in types:
            if t['key'] == activity_type:
                return t['name']
        return activity_type

    def _get_unit(self, category: str, activity_type: str) -> str:
        types = self.dm.get_activity_types(category)
        for t in types:
            if t['key'] == activity_type:
                return t['unit']
        return ''
