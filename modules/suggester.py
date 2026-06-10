from datetime import date
from typing import List, Dict, Tuple
from collections import defaultdict

from .data_manager import DataManager
from .calculator import CarbonCalculator


class Suggester:
    DIFFICULTY_NAMES = {
        'easy': '简单',
        'medium': '中等',
        'hard': '困难'
    }

    IMPACT_NAMES = {
        'low': '较小',
        'medium': '中等',
        'high': '较大',
        'very_high': '很大'
    }

    def __init__(self, data_manager: DataManager, calculator: CarbonCalculator):
        self.dm = data_manager
        self.calc = calculator
        self.suggestions = data_manager.suggestions

    def analyze_user_profile(self, user_id: str) -> Dict:
        user = self.dm.get_user(user_id)
        if not user:
            return {}

        today = date.today()
        weekly = self.calc.calculate_period_emission(user_id, 'weekly', today)
        monthly = self.calc.calculate_period_emission(user_id, 'monthly', today)

        weekly_car_km = 0
        weekly_flying_count = 0
        weekly_meat_count = defaultdict(int)
        monthly_electricity = 0
        monthly_shopping_items = defaultdict(int)
        monthly_heating = 0
        weekly_dairy_count = 0
        gasoline_car_detected = False

        for activity in weekly['detailed_activities']:
            if activity['category'] == 'transport':
                if activity['activity_type'] in ['car_gasoline', 'car_diesel', 'car_hybrid']:
                    weekly_car_km += activity['amount']
                    if activity['activity_type'] == 'car_gasoline':
                        gasoline_car_detected = True
                if activity['activity_type'] in ['airplane_short', 'airplane_long']:
                    weekly_flying_count += 1
            if activity['category'] == 'food':
                if activity['activity_type'] in ['beef', 'pork', 'chicken', 'fish', 'seafood']:
                    weekly_meat_count[activity['activity_type']] += activity['amount']
                if activity['activity_type'] == 'dairy':
                    weekly_dairy_count += activity['amount']

        for activity in monthly['detailed_activities']:
            if activity['category'] == 'electricity':
                monthly_electricity += activity['amount']
            if activity['category'] == 'shopping':
                monthly_shopping_items[activity['activity_type']] += activity['amount']
            if activity['category'] == 'heating':
                monthly_heating += activity['amount']

        total_meat_servings = sum(weekly_meat_count.values())

        profile = {
            'weekly_car_km': weekly_car_km,
            'weekly_flying_count': weekly_flying_count,
            'weekly_beef_servings': weekly_meat_count.get('beef', 0),
            'weekly_total_meat_servings': total_meat_servings,
            'weekly_dairy_servings': weekly_dairy_count,
            'monthly_electricity_kwh': monthly_electricity,
            'monthly_shopping_items': sum(monthly_shopping_items.values()),
            'monthly_clothing_items': monthly_shopping_items.get('clothing', 0),
            'monthly_electronics_items': monthly_shopping_items.get('electronics', 0),
            'monthly_heating_units': monthly_heating,
            'gasoline_car_detected': gasoline_car_detected,
            'monthly_emission': monthly['total_emission'],
            'category_breakdown': monthly['category_breakdown']
        }

        return profile

    def match_conditions(self, profile: Dict) -> List[str]:
        conditions = []

        if profile.get('weekly_car_km', 0) >= 200:
            conditions.append('high_car_usage')
        elif profile.get('weekly_car_km', 0) >= 100:
            conditions.append('high_car_usage')

        if profile.get('weekly_flying_count', 0) >= 2:
            conditions.append('frequent_flying')

        if profile.get('gasoline_car_detected', False):
            conditions.append('gasoline_car')

        if profile.get('weekly_beef_servings', 0) >= 2:
            conditions.append('high_meat_consumption')
        elif profile.get('weekly_total_meat_servings', 0) >= 10:
            conditions.append('high_meat_consumption')

        if profile.get('weekly_dairy_servings', 0) >= 5:
            conditions.append('high_dairy')

        if profile.get('monthly_electricity_kwh', 0) >= 400:
            conditions.append('high_electricity')
        elif profile.get('monthly_electricity_kwh', 0) >= 300:
            conditions.append('high_electricity')
        elif profile.get('monthly_electricity_kwh', 0) >= 200:
            conditions.append('high_electricity')

        if profile.get('monthly_shopping_items', 0) >= 10:
            conditions.append('high_shopping')

        if profile.get('monthly_clothing_items', 0) >= 3:
            conditions.append('high_clothing')

        if profile.get('monthly_electronics_items', 0) * 12 >= 2:
            conditions.append('high_electronics')

        if profile.get('monthly_heating_units', 0) >= 200:
            conditions.append('high_heating')

        conditions.append('general')

        return conditions

    def calculate_suggestion_score(self, suggestion: Dict, profile: Dict,
                                    matched_conditions: List[str]) -> float:
        score = 0.0
        condition = suggestion.get('condition', 'general')

        if condition in matched_conditions:
            score += 10.0

            if condition == 'high_car_usage':
                score += min(profile.get('weekly_car_km', 0) / 50, 10)
            elif condition == 'high_electricity':
                score += min(profile.get('monthly_electricity_kwh', 0) / 50, 10)
            elif condition == 'high_meat_consumption':
                score += min(profile.get('weekly_total_meat_servings', 0) / 2, 10)
            elif condition == 'high_shopping':
                score += min(profile.get('monthly_shopping_items', 0) / 2, 10)

        impact = suggestion.get('impact', 'medium')
        impact_scores = {'low': 1, 'medium': 3, 'high': 6, 'very_high': 10}
        score += impact_scores.get(impact, 3)

        difficulty = suggestion.get('difficulty', 'medium')
        diff_bonus = {'easy': 5, 'medium': 2, 'hard': 0}
        score += diff_bonus.get(difficulty, 2)

        saving = suggestion.get('saving_estimation', {}).get('saving_kg_co2', 0)
        score += min(saving / 10, 10)

        return score

    def get_suggestions(self, user_id: str, count: int = 3) -> List[Dict]:
        profile = self.analyze_user_profile(user_id)
        if not profile:
            return []

        matched_conditions = self.match_conditions(profile)

        scored_suggestions = []
        for suggestion in self.suggestions:
            score = self.calculate_suggestion_score(suggestion, profile, matched_conditions)
            scored_suggestions.append((score, suggestion))

        scored_suggestions.sort(key=lambda x: x[0], reverse=True)

        selected = []
        used_categories = set()
        used_ids = set()

        for score, suggestion in scored_suggestions:
            if len(selected) >= count:
                break

            cat = suggestion.get('category')
            sid = suggestion.get('id')

            if cat in used_categories and len(used_categories) < len(selected) + 1:
                continue

            if sid in used_ids:
                continue

            enriched = self._enrich_suggestion(suggestion, profile)
            enriched['match_score'] = round(score, 1)
            selected.append(enriched)
            used_categories.add(cat)
            used_ids.add(sid)

        if len(selected) < count:
            for score, suggestion in scored_suggestions:
                if len(selected) >= count:
                    break
                if suggestion.get('id') in used_ids:
                    continue
                enriched = self._enrich_suggestion(suggestion, profile)
                enriched['match_score'] = round(score, 1)
                selected.append(enriched)
                used_ids.add(suggestion.get('id'))

        return selected

    def _enrich_suggestion(self, suggestion: Dict, profile: Dict) -> Dict:
        saving = suggestion.get('saving_estimation', {})
        base_saving = saving.get('saving_kg_co2', 0)

        monthly_emission = profile.get('monthly_emission', 0)
        if monthly_emission > 0 and base_saving > 0:
            impact_percent = round(base_saving / monthly_emission * 100, 1)
        else:
            impact_percent = 0

        enriched = {
            **suggestion,
            'difficulty_name': self.DIFFICULTY_NAMES.get(suggestion.get('difficulty', 'medium'), '中等'),
            'impact_name': self.IMPACT_NAMES.get(suggestion.get('impact', 'medium'), '中等'),
            'calculated_saving_kg': base_saving,
            'impact_percent': impact_percent
        }

        return enriched

    def format_suggestion_card(self, suggestion: Dict, index: int) -> str:
        lines = []
        diff = suggestion.get('difficulty_name', '')
        impact = suggestion.get('impact_name', '')
        saving = suggestion.get('calculated_saving_kg', 0)
        impact_pct = suggestion.get('impact_percent', 0)

        lines.append(f'  [{index}] {suggestion.get("title", "")}')
        lines.append(f'      ├─ 难度: {diff}  |  效果: {impact}  |  预计月减排: {saving:.1f}kg ({impact_pct:.1f}%)')
        lines.append(f'      ├─ {suggestion.get("description", "")}')

        tips = suggestion.get('tips', [])
        if tips:
            lines.append(f'      └─ 小贴士:')
            for i, tip in enumerate(tips):
                prefix = '         · ' if i < len(tips) - 1 else '         └· '
                lines.append(f'{prefix}{tip}')

        lines.append('')
        return '\n'.join(lines)

    def get_total_potential_saving(self, suggestions: List[Dict]) -> Dict:
        total_monthly = sum(s.get('calculated_saving_kg', 0) for s in suggestions)
        return {
            'monthly_saving_kg': round(total_monthly, 1),
            'yearly_saving_kg': round(total_monthly * 12, 1),
            'monthly_saving_trees': round(total_monthly * 12 / 18, 1),
            'yearly_saving_trees': round(total_monthly * 12 / 18, 1)
        }
