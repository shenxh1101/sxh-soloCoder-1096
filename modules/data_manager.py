import json
import os
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any


class DataManager:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.users_dir = self.data_dir / 'users'
        self.users_dir.mkdir(exist_ok=True)

        self.emission_factors = self._load_json(self.data_dir / 'emission_factors.json')
        self.suggestions = self._load_json(self.data_dir / 'suggestions.json')

    @staticmethod
    def _load_json(filepath: Path) -> Any:
        if not filepath.exists():
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _save_json(filepath: Path, data: Any) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_user_filepath(self, user_id: str) -> Path:
        return self.users_dir / f'{user_id}.json'

    def _load_user_data(self, user_id: str) -> Dict:
        filepath = self._get_user_filepath(user_id)
        if not filepath.exists():
            raise FileNotFoundError(f'用户档案不存在: {user_id}')
        return self._load_json(filepath)

    def _save_user_data(self, user_id: str, data: Dict) -> None:
        filepath = self._get_user_filepath(user_id)
        self._save_json(filepath, data)

    def create_user(self, name: str, region: str = 'national_average',
                    household_size: int = 1, description: str = '') -> Dict:
        user_id = str(uuid.uuid4())[:8]
        user_data = {
            'user_id': user_id,
            'name': name,
            'region': region,
            'household_size': household_size,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'activities': [],
            'goals': [],
            'templates': [],
            'stats': {}
        }
        self._save_user_data(user_id, user_data)
        return user_data

    def list_users(self) -> List[Dict]:
        users = []
        for filepath in self.users_dir.glob('*.json'):
            try:
                user_data = self._load_json(filepath)
                users.append({
                    'user_id': user_data['user_id'],
                    'name': user_data['name'],
                    'region': user_data.get('region', 'national_average'),
                    'household_size': user_data.get('household_size', 1),
                    'activity_count': len(user_data.get('activities', [])),
                    'created_at': user_data.get('created_at', '')
                })
            except Exception:
                continue
        users.sort(key=lambda x: x.get('created_at', ''))
        return users

    def get_user(self, user_id: str) -> Optional[Dict]:
        try:
            return self._load_user_data(user_id)
        except FileNotFoundError:
            return None

    def update_user(self, user_id: str, **kwargs) -> Optional[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return None
        for key in ['name', 'region', 'household_size', 'description']:
            if key in kwargs:
                user_data[key] = kwargs[key]
        self._save_user_data(user_id, user_data)
        return user_data

    def delete_user(self, user_id: str) -> bool:
        filepath = self._get_user_filepath(user_id)
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def add_activity(self, user_id: str, category: str, activity_type: str,
                     amount: float, activity_date: str = None,
                     notes: str = '', template_id: str = None) -> Optional[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return None

        if activity_date is None:
            activity_date = date.today().isoformat()

        activity_id = str(uuid.uuid4())[:12]
        activity = {
            'activity_id': activity_id,
            'category': category,
            'activity_type': activity_type,
            'amount': amount,
            'activity_date': activity_date,
            'notes': notes,
            'created_at': datetime.now().isoformat()
        }
        if template_id:
            activity['template_id'] = template_id
        user_data['activities'].append(activity)
        self._save_user_data(user_id, user_data)
        return activity

    def get_activity(self, user_id: str, activity_id: str) -> Optional[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return None

        for act in user_data.get('activities', []):
            if act['activity_id'] == activity_id:
                return act
        return None

    def list_activities(self, user_id: str, start_date: str = None,
                        end_date: str = None, category: str = None,
                        limit: int = None) -> List[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return []

        activities = user_data.get('activities', [])

        if start_date:
            activities = [a for a in activities if a['activity_date'] >= start_date]
        if end_date:
            activities = [a for a in activities if a['activity_date'] <= end_date]
        if category:
            activities = [a for a in activities if a['category'] == category]

        activities.sort(key=lambda x: x['activity_date'], reverse=True)
        if limit:
            activities = activities[:limit]
        return activities

    def delete_activity(self, user_id: str, activity_id: str) -> bool:
        user_data = self.get_user(user_id)
        if user_data is None:
            return False

        activities = user_data.get('activities', [])
        original_len = len(activities)
        user_data['activities'] = [a for a in activities if a['activity_id'] != activity_id]

        if len(user_data['activities']) < original_len:
            self._save_user_data(user_id, user_data)
            return True
        return False

    def bulk_add_activities(self, user_id: str, activities: List[Dict]) -> List[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return []

        added = []
        for act in activities:
            activity_id = str(uuid.uuid4())[:12]
            activity = {
                'activity_id': activity_id,
                'category': act['category'],
                'activity_type': act['activity_type'],
                'amount': float(act['amount']),
                'activity_date': act.get('activity_date', date.today().isoformat()),
                'notes': act.get('notes', ''),
                'created_at': datetime.now().isoformat()
            }
            if act.get('template_id'):
                activity['template_id'] = act['template_id']
            user_data['activities'].append(activity)
            added.append(activity)

        self._save_user_data(user_id, user_data)
        return added

    def create_template(self, user_id: str, name: str, category: str,
                        activity_type: str, default_amount: float,
                        default_notes: str = '', period: str = 'on_demand',
                        status: str = 'active') -> Optional[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return None

        if not self._validate_category(category):
            return None
        if not self._validate_activity_type(category, activity_type):
            return None

        template_id = str(uuid.uuid4())[:8]
        template = {
            'template_id': template_id,
            'name': name,
            'category': category,
            'activity_type': activity_type,
            'default_amount': default_amount,
            'default_notes': default_notes,
            'period': period,
            'status': status,
            'skip_dates': [],
            'created_at': datetime.now().isoformat(),
            'last_used_at': None,
            'usage_count': 0,
            'generated_record_ids': []
        }
        user_data['templates'].append(template)
        self._save_user_data(user_id, user_data)
        return template

    def list_templates(self, user_id: str, category: str = None,
                        period: str = None) -> List[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return []

        templates = user_data.get('templates', [])
        if category:
            templates = [t for t in templates if t['category'] == category]
        if period:
            templates = [t for t in templates if t['period'] == period]

        templates.sort(key=lambda x: x.get('usage_count', 0), reverse=True)
        return templates

    def get_template(self, user_id: str, template_id: str) -> Optional[Dict]:
        templates = self.list_templates(user_id)
        for t in templates:
            if t['template_id'] == template_id:
                return t
        return None

    def apply_template(self, user_id: str, template_id: str,
                        custom_amount: float = None,
                        custom_notes: str = None,
                        activity_date: str = None,
                        generate_period: str = None) -> List[Dict]:
        template = self.get_template(user_id, template_id)
        if not template:
            return []

        user_data = self.get_user(user_id)
        if user_data is None:
            return []

        amount = custom_amount if custom_amount is not None else template['default_amount']
        notes = custom_notes if custom_notes is not None else template['default_notes']

        if activity_date is None:
            activity_date = date.today().isoformat()

        activities = []
        if generate_period == 'daily':
            d = date.fromisoformat(activity_date)
            for i in range(7):
                act_date = (d + timedelta(days=i)).isoformat()
                activity = self.add_activity(user_id, template['category'],
                                             template['activity_type'], amount,
                                             act_date, notes)
                if activity:
                    activities.append(activity)
        elif generate_period == 'weekly':
            d = date.fromisoformat(activity_date)
            week_start = d - timedelta(days=d.weekday())
            for i in range(7):
                act_date = (week_start + timedelta(days=i)).isoformat()
                activity = self.add_activity(user_id, template['category'],
                                             template['activity_type'], amount,
                                             act_date, notes)
                if activity:
                    activities.append(activity)
        else:
            activity = self.add_activity(user_id, template['category'],
                                         template['activity_type'], amount,
                                         activity_date, notes)
            if activity:
                activities.append(activity)

        for t in user_data.get('templates', []):
            if t['template_id'] == template_id:
                t['usage_count'] = t.get('usage_count', 0) + len(activities)
                t['last_used_at'] = datetime.now().isoformat()
                break
        self._save_user_data(user_id, user_data)

        return activities

    def update_template(self, user_id: str, template_id: str, **kwargs) -> Optional[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return None

        for t in user_data.get('templates', []):
            if t['template_id'] == template_id:
                for key in ['name', 'category', 'activity_type', 'default_amount',
                            'default_notes', 'period']:
                    if key in kwargs:
                        if key in ['category', 'activity_type']:
                            if key == 'category' and not self._validate_category(kwargs[key]):
                                continue
                            if key == 'activity_type':
                                cat = kwargs.get('category', t['category'])
                                if not self._validate_activity_type(cat, kwargs[key]):
                                    continue
                        t[key] = kwargs[key]
                self._save_user_data(user_id, user_data)
                return t
        return None

    def delete_template(self, user_id: str, template_id: str) -> bool:
        user_data = self.get_user(user_id)
        if user_data is None:
            return False

        templates = user_data.get('templates', [])
        original_len = len(templates)
        user_data['templates'] = [t for t in templates if t['template_id'] != template_id]

        if len(user_data['templates']) < original_len:
            self._save_user_data(user_id, user_data)
            return True
        return False

    def pause_template(self, user_id: str, template_id: str) -> bool:
        user_data = self.get_user(user_id)
        if user_data is None:
            return False

        for t in user_data.get('templates', []):
            if t['template_id'] == template_id:
                t['status'] = 'paused'
                self._save_user_data(user_id, user_data)
                return True
        return False

    def resume_template(self, user_id: str, template_id: str) -> bool:
        user_data = self.get_user(user_id)
        if user_data is None:
            return False

        for t in user_data.get('templates', []):
            if t['template_id'] == template_id:
                t['status'] = 'active'
                self._save_user_data(user_id, user_data)
                return True
        return False

    def skip_template_date(self, user_id: str, template_id: str,
                           skip_date: str) -> bool:
        user_data = self.get_user(user_id)
        if user_data is None:
            return False

        for t in user_data.get('templates', []):
            if t['template_id'] == template_id:
                if 'skip_dates' not in t:
                    t['skip_dates'] = []
                if skip_date not in t['skip_dates']:
                    t['skip_dates'].append(skip_date)
                    t['skip_dates'].sort()
                self._save_user_data(user_id, user_data)
                return True
        return False

    def unskip_template_date(self, user_id: str, template_id: str,
                              skip_date: str) -> bool:
        user_data = self.get_user(user_id)
        if user_data is None:
            return False

        for t in user_data.get('templates', []):
            if t['template_id'] == template_id:
                if skip_date in t.get('skip_dates', []):
                    t['skip_dates'].remove(skip_date)
                self._save_user_data(user_id, user_data)
                return True
        return False

    def get_schedule_preview(self, user_id: str, start_date: str = None,
                              end_date: str = None) -> List[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return []

        if start_date is None:
            start_date = date.today().isoformat()
        if end_date is None:
            end_dt = date.today() + timedelta(days=30)
            end_date = end_dt.isoformat()

        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        days = (end_dt - start_dt).days + 1

        schedule = []
        templates = [t for t in user_data.get('templates', [])
                     if t.get('status', 'active') == 'active'
                     and t.get('period', 'on_demand') in ['daily', 'weekly', 'monthly']]

        for template in templates:
            period = template['period']
            skip_dates = template.get('skip_dates', [])

            for i in range(days):
                d = start_dt + timedelta(days=i)
                d_str = d.isoformat()

                if d_str in skip_dates:
                    continue

                should_generate = False
                if period == 'daily':
                    should_generate = True
                elif period == 'weekly':
                    should_generate = True
                elif period == 'monthly':
                    if d.day == 1:
                        should_generate = True

                if should_generate:
                    existing = self._find_activity_by_date(user_id, template['template_id'], d_str)
                    schedule.append({
                        'date': d_str,
                        'template_id': template['template_id'],
                        'template_name': template['name'],
                        'category': template['category'],
                        'activity_type': template['activity_type'],
                        'amount': template['default_amount'],
                        'notes': template.get('default_notes', ''),
                        'period': period,
                        'status': 'generated' if existing else 'planned',
                        'activity_id': existing['activity_id'] if existing else None
                    })

        schedule.sort(key=lambda x: (x['date'], x['template_name']))
        return schedule

    def _find_activity_by_date(self, user_id: str, template_id: str,
                                activity_date: str) -> Optional[Dict]:
        activities = self.list_activities(user_id, start_date=activity_date,
                                           end_date=activity_date)
        for act in activities:
            if act.get('template_id') == template_id:
                return act
        return None

    def generate_scheduled_activities(self, user_id: str,
                                       start_date: str = None,
                                       end_date: str = None) -> List[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return []

        schedule = self.get_schedule_preview(user_id, start_date, end_date)
        generated = []

        for item in schedule:
            if item['status'] == 'planned':
                activity = self.add_activity(
                    user_id,
                    category=item['category'],
                    activity_type=item['activity_type'],
                    amount=item['amount'],
                    activity_date=item['date'],
                    notes=item['notes'] + f' [计划生成:{item["template_name"]}]',
                    template_id=item['template_id']
                )
                if activity:
                    generated.append(activity)

        if generated:
            user_data = self.get_user(user_id)
            for item in schedule:
                if item['status'] == 'planned':
                    for t in user_data.get('templates', []):
                        if t['template_id'] == item['template_id']:
                            if 'generated_record_ids' not in t:
                                t['generated_record_ids'] = []
                            for act in generated:
                                if act.get('template_id') == item['template_id'] \
                                   and act['activity_date'] == item['date']:
                                    if act['activity_id'] not in t['generated_record_ids']:
                                        t['generated_record_ids'].append(act['activity_id'])
                            t['usage_count'] = t.get('usage_count', 0) + 1
                            t['last_used_at'] = datetime.now().isoformat()
                            break
            self._save_user_data(user_id, user_data)

        return generated

    def get_template_generated_activities(self, user_id: str,
                                            template_id: str) -> List[Dict]:
        template = self.get_template(user_id, template_id)
        if not template:
            return []

        record_ids = template.get('generated_record_ids', [])
        activities = []
        for aid in record_ids:
            act = self.get_activity(user_id, aid)
            if act:
                activities.append(act)
        return activities

    def _validate_category(self, category: str) -> bool:
        return category in self.get_categories()

    def _validate_activity_type(self, category: str, activity_type: str) -> bool:
        if category == 'electricity' and activity_type == 'grid_electricity':
            return True
        valid_types = [t['key'] for t in self.get_activity_types(category)]
        return activity_type in valid_types

    def set_goal(self, user_id: str, goal_type: str, target_value: float,
                 period: str = 'monthly', start_date: str = None,
                 description: str = '') -> Optional[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return None

        if start_date is None:
            start_date = date.today().isoformat()

        goal_id = str(uuid.uuid4())[:8]
        goal = {
            'goal_id': goal_id,
            'goal_type': goal_type,
            'target_value': target_value,
            'period': period,
            'start_date': start_date,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'achieved_at': None
        }
        user_data['goals'].append(goal)
        self._save_user_data(user_id, user_data)
        return goal

    def list_goals(self, user_id: str, active_only: bool = True) -> List[Dict]:
        user_data = self.get_user(user_id)
        if user_data is None:
            return []

        goals = user_data.get('goals', [])
        if active_only:
            goals = [g for g in goals if g.get('achieved_at') is None]
        return goals

    def mark_goal_achieved(self, user_id: str, goal_id: str) -> bool:
        user_data = self.get_user(user_id)
        if user_data is None:
            return False

        for goal in user_data.get('goals', []):
            if goal['goal_id'] == goal_id and goal.get('achieved_at') is None:
                goal['achieved_at'] = datetime.now().isoformat()
                self._save_user_data(user_id, user_data)
                return True
        return False

    def delete_goal(self, user_id: str, goal_id: str) -> bool:
        user_data = self.get_user(user_id)
        if user_data is None:
            return False

        goals = user_data.get('goals', [])
        original_len = len(goals)
        user_data['goals'] = [g for g in goals if g['goal_id'] != goal_id]

        if len(user_data['goals']) < original_len:
            self._save_user_data(user_id, user_data)
            return True
        return False

    @staticmethod
    def get_date_range(period: str, reference_date: date = None) -> (str, str):
        if reference_date is None:
            reference_date = date.today()

        if period == 'daily':
            start = reference_date
            end = reference_date
        elif period == 'weekly':
            start = reference_date - timedelta(days=reference_date.weekday())
            end = start + timedelta(days=6)
        elif period == 'monthly':
            start = reference_date.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1) - timedelta(days=1)
        elif period == 'yearly':
            start = reference_date.replace(month=1, day=1)
            end = reference_date.replace(month=12, day=31)
        else:
            raise ValueError(f'不支持的周期类型: {period}')

        return start.isoformat(), end.isoformat()

    def get_activities_by_period(self, user_id: str, period: str = 'monthly',
                                  reference_date: date = None) -> List[Dict]:
        start_date, end_date = self.get_date_range(period, reference_date)
        return self.list_activities(user_id, start_date=start_date, end_date=end_date)

    def get_categories(self) -> List[str]:
        return list(self.emission_factors.keys())

    def get_available_categories(self) -> List[str]:
        excluded = ['benchmarks']
        result = []
        for cat in self.emission_factors.keys():
            if cat in excluded:
                continue
            types = self.get_activity_types(cat)
            if cat == 'electricity':
                result.append(cat)
            elif types:
                result.append(cat)
        return result

    def get_activity_types(self, category: str) -> List[Dict]:
        cat_data = self.emission_factors.get(category, {})
        if isinstance(cat_data, dict):
            result = []
            for key, info in cat_data.items():
                if isinstance(info, dict) and 'name' in info and 'factor' in info:
                    result.append({
                        'key': key,
                        'name': info.get('name', key),
                        'factor': info.get('factor', 0),
                        'unit': info.get('unit', '')
                    })
            return result
        return []

    def get_benchmarks(self) -> Dict:
        return self.emission_factors.get('benchmarks', {})
