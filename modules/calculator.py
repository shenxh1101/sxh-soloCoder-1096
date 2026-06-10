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
