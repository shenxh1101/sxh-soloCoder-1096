from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from .data_manager import DataManager


class CarbonCalculator:
    CATEGORY_NAMES = {
        'transport': '交通出行',
        'electricity': '电力消耗',
        'food': '饮食消费',
        'shopping': '购物消费',
        'heating': '采暖能源',
        'water': '水资源',
        'waste': '废弃物'
    }

    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
        self.factors = data_manager.emission_factors

    def calculate_activity_emission(self, activity: Dict, region: str = 'national_average') -> float:
        category = activity['category']
        activity_type = activity['activity_type']
        amount = activity['amount']

        factor = self._get_factor(category, activity_type, region)
        if category == 'food':
            serving_size = self._get_serving_size(category, activity_type)
            if serving_size:
                return round(amount * factor * serving_size, 4)
        return round(amount * factor, 4)

    def _get_factor(self, category: str, activity_type: str, region: str = 'national_average') -> float:
        if category not in self.factors:
            return 0.0

        category_data = self.factors[category]
        if category == 'electricity':
            if activity_type == 'grid_electricity':
                region_data = category_data.get(region, category_data.get('national_average', {}))
                return region_data.get('factor', 0.6101)
            return category_data.get(activity_type, {}).get('factor', 0.0)

        if activity_type in category_data:
            return category_data[activity_type].get('factor', 0.0)
        return 0.0

    def _get_serving_size(self, category: str, activity_type: str) -> float:
        if category != 'food':
            return 0.0
        return self.factors.get(category, {}).get(activity_type, {}).get('serving_size', 0.0)

    def calculate_period_emission(self, user_id: str, period: str = 'monthly',
                                   reference_date: date = None) -> Dict:
        activities = self.dm.get_activities_by_period(user_id, period, reference_date)
        user = self.dm.get_user(user_id)
        region = user.get('region', 'national_average') if user else 'national_average'

        total_emission = 0.0
        category_emissions = defaultdict(float)
        type_emissions = defaultdict(float)
        detailed_activities = []

        for activity in activities:
            emission = self.calculate_activity_emission(activity, region)
            total_emission += emission
            category_emissions[activity['category']] += emission
            type_emissions[activity['activity_type']] += emission
            detailed_activities.append({
                **activity,
                'emission': emission,
                'category_name': self.CATEGORY_NAMES.get(activity['category'], activity['category']),
                'activity_name': self._get_activity_name(activity['category'], activity['activity_type'])
            })

        category_breakdown = []
        for cat, emis in sorted(category_emissions.items(), key=lambda x: x[1], reverse=True):
            percentage = (emis / total_emission * 100) if total_emission > 0 else 0
            category_breakdown.append({
                'category': cat,
                'category_name': self.CATEGORY_NAMES.get(cat, cat),
                'emission': round(emis, 2),
                'percentage': round(percentage, 2)
            })

        type_breakdown = []
        for typ, emis in sorted(type_emissions.items(), key=lambda x: x[1], reverse=True):
            percentage = (emis / total_emission * 100) if total_emission > 0 else 0
            type_breakdown.append({
                'type': typ,
                'type_name': self._get_activity_name(self._find_type_category(typ), typ),
                'emission': round(emis, 2),
                'percentage': round(percentage, 2)
            })

        start_date, end_date = self.dm.get_date_range(period, reference_date)

        return {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'total_emission': round(total_emission, 2),
            'category_breakdown': category_breakdown,
            'type_breakdown': type_breakdown,
            'activity_count': len(activities),
            'detailed_activities': detailed_activities
        }

    def _find_type_category(self, activity_type: str) -> str:
        for category, types in self.factors.items():
            if category == 'benchmarks':
                continue
            if isinstance(types, dict) and activity_type in types:
                return category
        return 'unknown'

    def _get_activity_name(self, category: str, activity_type: str) -> str:
        if category not in self.factors:
            return activity_type
        category_data = self.factors[category]
        if isinstance(category_data, dict):
            if activity_type in category_data and isinstance(category_data[activity_type], dict):
                return category_data[activity_type].get('name', activity_type)
        return activity_type

    def calculate_trend(self, user_id: str, periods: int = 6,
                        period_type: str = 'monthly',
                        end_date: date = None) -> Dict:
        if end_date is None:
            end_date = date.today()

        trend_data = []
        period_labels = []

        for i in range(periods - 1, -1, -1):
            if period_type == 'daily':
                ref_date = end_date - timedelta(days=i)
                start, end = self.dm.get_date_range('daily', ref_date)
                label = ref_date.strftime('%m-%d')
            elif period_type == 'weekly':
                ref_date = end_date - timedelta(weeks=i)
                start, end = self.dm.get_date_range('weekly', ref_date)
                label = f"{ref_date.strftime('%m/%d')}周"
            elif period_type == 'monthly':
                month = end_date.month - i
                year = end_date.year
                while month <= 0:
                    month += 12
                    year -= 1
                ref_date = end_date.replace(year=year, month=month, day=1)
                start, end = self.dm.get_date_range('monthly', ref_date)
                label = ref_date.strftime('%Y年%m月')
            else:
                raise ValueError(f'不支持的周期类型: {period_type}')

            result = self.calculate_period_emission(user_id, period_type, ref_date)
            trend_data.append(result['total_emission'])
            period_labels.append(label)

        benchmarks = self.dm.get_benchmarks()
        benchmark_value = benchmarks.get(f'china_{period_type}_per_capita', 0)

        return {
            'period_type': period_type,
            'periods': periods,
            'labels': period_labels,
            'values': trend_data,
            'average': round(sum(trend_data) / len(trend_data), 2) if trend_data else 0,
            'benchmark': benchmark_value,
            'min': round(min(trend_data), 2) if trend_data else 0,
            'max': round(max(trend_data), 2) if trend_data else 0
        }

    def compare_with_benchmark(self, user_id: str, period: str = 'monthly',
                                reference_date: date = None) -> Dict:
        result = self.calculate_period_emission(user_id, period, reference_date)
        benchmarks = self.dm.get_benchmarks()

        china_benchmark = benchmarks.get(f'china_{period}_per_capita', 0)
        global_benchmark = benchmarks.get(f'global_{period}_per_capita', 0)
        eu_benchmark = benchmarks.get(f'eu_{period}_per_capita', 0)

        user_value = result['total_emission']

        return {
            'period': period,
            'user_emission': user_value,
            'china_average': china_benchmark,
            'global_average': global_benchmark,
            'eu_average': eu_benchmark,
            'vs_china_percent': round((user_value - china_benchmark) / china_benchmark * 100, 1) if china_benchmark > 0 else 0,
            'vs_global_percent': round((user_value - global_benchmark) / global_benchmark * 100, 1) if global_benchmark > 0 else 0,
            'vs_eu_percent': round((user_value - eu_benchmark) / eu_benchmark * 100, 1) if eu_benchmark > 0 else 0
        }

    def check_goal_progress(self, user_id: str, goal: Dict,
                             reference_date: date = None) -> Dict:
        if reference_date is None:
            reference_date = date.today()

        goal_type = goal['goal_type']
        period = goal.get('period', 'monthly')
        target = goal['target_value']

        result = self.calculate_period_emission(user_id, period, reference_date)

        if goal_type == 'total_emission':
            current = result['total_emission']
        else:
            current = 0
            for cat in result['category_breakdown']:
                if cat['category'] == goal_type:
                    current = cat['emission']
                    break

        progress = (target - current) / target * 100 if target > 0 else 0
        achieved = current <= target

        return {
            'goal_id': goal['goal_id'],
            'goal_type': goal_type,
            'target': target,
            'current': round(current, 2),
            'progress_percent': round(progress, 1),
            'achieved': achieved,
            'remaining': round(max(0, target - current), 2),
            'overage': round(max(0, current - target), 2)
        }

    def get_all_goals_progress(self, user_id: str, reference_date: date = None) -> List[Dict]:
        goals = self.dm.list_goals(user_id, active_only=True)
        return [self.check_goal_progress(user_id, g, reference_date) for g in goals]

    def predict_goal_outcome(self, user_id: str, goal: Dict,
                              reference_date: date = None,
                              lookback_periods: int = 4) -> Dict:
        if reference_date is None:
            reference_date = date.today()

        goal_type = goal['goal_type']
        period = goal.get('period', 'monthly')
        target = goal['target_value']

        start_date, end_date = self.dm.get_date_range(period, reference_date)
        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        days_total = (end_dt - start_dt).days + 1
        days_passed = (reference_date - start_dt).days + 1
        days_remaining = days_total - days_passed
        if days_remaining < 0:
            days_remaining = 0

        current_result = self.calculate_period_emission(user_id, period, reference_date)

        if goal_type == 'total_emission':
            current = current_result['total_emission']
        else:
            current = 0
            for cat in current_result['category_breakdown']:
                if cat['category'] == goal_type:
                    current = cat['emission']
                    break

        historical_averages = []
        for i in range(1, lookback_periods + 1):
            if period == 'monthly':
                month = reference_date.month - i
                year = reference_date.year
                while month <= 0:
                    month += 12
                    year -= 1
                ref = reference_date.replace(year=year, month=month, day=1)
            elif period == 'weekly':
                ref = reference_date - timedelta(weeks=i)
            else:
                ref = reference_date - timedelta(days=i)

            hist_result = self.calculate_period_emission(user_id, period, ref)
            if goal_type == 'total_emission':
                hist_emission = hist_result['total_emission']
            else:
                hist_emission = 0
                for cat in hist_result['category_breakdown']:
                    if cat['category'] == goal_type:
                        hist_emission = cat['emission']
                        break
            if hist_emission > 0:
                historical_averages.append(hist_emission)

        if historical_averages:
            avg_daily = sum(historical_averages) / len(historical_averages) / days_total
        else:
            avg_daily = current / max(days_passed, 1)

        projected_total = current + (avg_daily * days_remaining)
        projected_over = max(0, projected_total - target)
        projected_under = max(0, target - projected_total)

        if projected_under > 0:
            will_achieve = True
            risk_level = 'low'
            risk_desc = '✓ 预计可顺利达标'
        elif projected_over <= target * 0.1:
            will_achieve = False
            risk_level = 'medium'
            risk_desc = '⚠️ 有小幅超标风险，需稍加注意'
        elif projected_over <= target * 0.3:
            will_achieve = False
            risk_level = 'high'
            risk_desc = '⚠️ 有较大超标风险，需要采取减排措施'
        else:
            will_achieve = False
            risk_level = 'critical'
            risk_desc = '❌ 预计将大幅超标，急需减排'

        remaining_quota = max(0, target - current)
        daily_quota = remaining_quota / max(days_remaining, 1) if days_remaining > 0 else 0

        return {
            'goal_id': goal['goal_id'],
            'goal_type': goal_type,
            'target': target,
            'current': round(current, 2),
            'days_total': days_total,
            'days_passed': days_passed,
            'days_remaining': days_remaining,
            'period_progress': round(days_passed / days_total * 100, 1) if days_total > 0 else 0,
            'emission_progress': round(current / target * 100, 1) if target > 0 else 0,
            'remaining_quota': round(remaining_quota, 2),
            'daily_quota': round(daily_quota, 2),
            'avg_daily_emission': round(avg_daily, 3),
            'projected_total': round(projected_total, 2),
            'projected_over': round(projected_over, 2),
            'projected_under': round(projected_under, 2),
            'will_achieve': will_achieve,
            'risk_level': risk_level,
            'risk_description': risk_desc,
            'historical_periods_used': len(historical_averages)
        }

    def get_all_goals_prediction(self, user_id: str,
                                  reference_date: date = None,
                                  lookback_periods: int = 4) -> List[Dict]:
        goals = self.dm.list_goals(user_id, active_only=True)
        return [self.predict_goal_outcome(user_id, g, reference_date, lookback_periods) for g in goals]

    def get_budget_alert(self, user_id: str,
                         reference_date: date = None,
                         period: str = 'daily') -> Dict:
        if reference_date is None:
            reference_date = date.today()

        goals = self.dm.list_goals(user_id, active_only=True)
        if not goals:
            return {'has_alert': False, 'alerts': [], 'budgets': []}

        alerts = []
        budgets = []

        for goal in goals:
            goal_type = goal['goal_type']
            target = goal['target_value']
            goal_period = goal.get('period', 'monthly')

            if goal_period == 'monthly':
                month_days = 30
                daily_budget = target / month_days
                weekly_budget = daily_budget * 7
                monthly_budget = target

                monthly_budget = target

            if period == 'daily':
                current = self.calculate_period_emission(user_id, 'daily', reference_date)
                if goal_type == 'total_emission':
                    current_emission = current['total_emission']
                else:
                    current_emission = 0
                    for cat in current['category_breakdown']:
                        if cat['category'] == goal_type:
                            current_emission = cat['emission']
                            break

                budget = daily_budget
                remaining = daily_budget - current_emission
                overage = current_emission - daily_budget

                if overage > 0:
                    severity = 'warning'
                    if overage > daily_budget * 0.5:
                        severity = 'critical'
                    elif overage > daily_budget * 0.2:
                        severity = 'warning'
                    else:
                        severity = 'mild'

                    suggestion = self._get_reduction_suggestion(user_id, goal_type, overage, period)

                    alerts.append({
                        'goal_id': goal['goal_id'],
                        'goal_type': goal_type,
                        'period': period,
                        'budget': round(daily_budget, 3),
                        'current': round(current_emission, 2),
                        'overage': round(overage, 2),
                        'remaining': round(max(0, remaining), 2),
                        'severity': severity,
                        'severity_name': {'mild': '轻微超支', 'warning': '中度超支', 'critical': '严重超支'}[severity],
                        'suggestion': suggestion
                    })

                budgets.append({
                    'goal_id': goal['goal_id'],
                    'goal_type': goal_type,
                    'daily_budget': round(daily_budget, 3),
                    'weekly_budget': round(weekly_budget, 2),
                    'monthly_budget': round(monthly_budget, 2),
                    'daily_used': round(current_emission, 2),
                    'daily_remaining': round(max(0, remaining), 2),
                    'overage': round(max(0, overage), 2)
                })

            elif period == 'weekly':
                current = self.calculate_period_emission(user_id, 'weekly', reference_date)
                if goal_type == 'total_emission':
                    current_emission = current['total_emission']
                else:
                    current_emission = 0
                    for cat in current['category_breakdown']:
                        if cat['category'] == goal_type:
                            current_emission = cat['emission']
                            break

                budget = weekly_budget
                remaining = weekly_budget - current_emission
                overage = current_emission - weekly_budget

                if overage > 0:
                    severity = 'warning'
                    if overage > weekly_budget * 0.5:
                        severity = 'critical'
                    elif overage > weekly_budget * 0.2:
                        severity = 'warning'
                    else:
                        severity = 'mild'

                    suggestion = self._get_reduction_suggestion(user_id, goal_type, overage, period)

                    alerts.append({
                        'goal_id': goal['goal_id'],
                        'goal_type': goal_type,
                        'period': period,
                        'budget': round(weekly_budget, 2),
                        'current': round(current_emission, 2),
                        'overage': round(overage, 2),
                        'remaining': round(max(0, remaining), 2),
                        'severity': severity,
                        'severity_name': {'mild': '轻微超支', 'warning': '中度超支', 'critical': '严重超支'}[severity],
                        'suggestion': suggestion
                    })

                budgets.append({
                    'goal_id': goal['goal_id'],
                    'goal_type': goal_type,
                    'daily_budget': round(daily_budget, 3),
                    'weekly_budget': round(weekly_budget, 2),
                    'monthly_budget': round(monthly_budget, 2),
                    'weekly_used': round(current_emission, 2),
                    'weekly_remaining': round(max(0, remaining), 2),
                    'overage': round(max(0, overage), 2)
                })

        return {
            'has_alert': len(alerts) > 0,
            'alert_count': len(alerts),
            'alerts': alerts,
            'budgets': budgets,
            'reference_date': reference_date.isoformat()
        }

    def _get_reduction_suggestion(self, user_id: str, goal_type: str,
                                overage: float, period: str) -> Dict:
        if goal_type == 'total_emission':
            result = self.calculate_period_emission(user_id, period)
            categories = result['category_breakdown']
            categories.sort(key=lambda x: x['emission'], reverse=True)

            if categories:
                top_cat = categories[0]
                reduction_ratio = overage / max(top_cat['emission'], 0.3)

                suggestions_map = {
                    'transport': {
                        'action': '减少驾车出行',
                        'detail': '尝试公共交通或骑行替代1-2次',
                        'tip': '建议优先从交通类减排，占比最高'
                    },
                    'electricity': {
                        'action': '节约用电',
                        'detail': '关闭不必要的电器，调高空调温度',
                        'tip': '建议优先从电力类减排'
                    },
                    'food': {
                        'action': '调整饮食结构',
                        'detail': '减少红肉换为鸡肉或素食',
                        'tip': '建议优先从饮食类减排'
                    },
                    'shopping': {
                        'action': '理性消费',
                        'detail': '减少不必要的购物',
                        'tip': '建议优先从购物类减排'
                    }
                }

                cat_key = top_cat['category']
                base_suggestion = suggestions_map.get(cat_key, {
                    'action': '减少高排放活动',
                    'detail': '减少高排放类活动频次',
                    'tip': '建议从排放最多的类别入手'
                })

                return {
                    'priority_category': cat_key,
                    'priority_category_name': top_cat['category_name'],
                    'category_emission': top_cat['emission'],
                    'suggested_reduction_ratio': round(reduction_ratio * 100, 1),
                    **base_suggestion
                }

        return {
            'priority_category': goal_type,
            'priority_category_name': self.CATEGORY_NAMES.get(goal_type, goal_type),
            'action': '减少相关活动',
            'detail': '适当减少该类活动的频次或数量',
            'tip': '建议从当前类别入手减排'
        }

    def get_dashboard_budget_summary(self, user_id: str) -> Dict:
        daily_alert = self.get_budget_alert(user_id, period='daily')
        weekly_alert = self.get_budget_alert(user_id, period='weekly')

        daily_over = False
        weekly_over = False

        daily_budget_info = {}
        weekly_budget_info = {}

        if daily_alert['budgets']:
            total_daily = [b for b in daily_alert['budgets'] if b['goal_type'] == 'total_emission']
            if total_daily:
                daily_budget_info = total_daily[0]
                daily_over = total_daily[0].get('overage', 0) > 0

        if weekly_alert['budgets']:
            total_weekly = [b for b in weekly_alert['budgets'] if b['goal_type'] == 'total_emission']
            if total_weekly:
                weekly_budget_info = total_weekly[0]
                weekly_over = total_weekly[0].get('overage', 0) > 0

        return {
            'daily': {
                'budget': daily_budget_info.get('daily_budget', 0),
                'used': daily_budget_info.get('daily_used', 0),
                'remaining': daily_budget_info.get('daily_remaining', 0),
                'overage': daily_budget_info.get('overage', 0),
                'is_over': daily_over
            },
            'weekly': {
                'budget': weekly_budget_info.get('weekly_budget', 0),
                'used': weekly_budget_info.get('weekly_used', 0),
                'remaining': weekly_budget_info.get('weekly_remaining', 0),
                'overage': weekly_budget_info.get('overage', 0),
                'is_over': weekly_over
            },
            'daily_alerts': daily_alert.get('alerts', []),
            'weekly_alerts': weekly_alert.get('alerts', []),
            'has_alert': daily_over or weekly_over
        }

    def get_user_summary(self, user_id: str) -> Dict:
        user = self.dm.get_user(user_id)
        if not user:
            return {}

        today = date.today()

        daily = self.calculate_period_emission(user_id, 'daily', today)
        weekly = self.calculate_period_emission(user_id, 'weekly', today)
        monthly = self.calculate_period_emission(user_id, 'monthly', today)

        benchmark_compare = self.compare_with_benchmark(user_id, 'monthly', today)
        goals_progress = self.get_all_goals_progress(user_id, today)

        all_activities = self.dm.list_activities(user_id)
        first_date = all_activities[-1]['activity_date'] if all_activities else None
        last_date = all_activities[0]['activity_date'] if all_activities else None

        trend = self.calculate_trend(user_id, periods=6, period_type='monthly', end_date=today)

        return {
            'user': {
                'user_id': user['user_id'],
                'name': user['name'],
                'region': user.get('region', 'national_average'),
                'household_size': user.get('household_size', 1)
            },
            'emissions': {
                'daily': daily['total_emission'],
                'weekly': weekly['total_emission'],
                'monthly': monthly['total_emission']
            },
            'category_breakdown': monthly['category_breakdown'],
            'benchmark_compare': benchmark_compare,
            'goals_progress': goals_progress,
            'activity_stats': {
                'total_count': len(all_activities),
                'first_date': first_date,
                'last_date': last_date
            },
            'trend': trend
        }
