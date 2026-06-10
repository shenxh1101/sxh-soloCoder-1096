import csv
import os
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from .data_manager import DataManager


class DataImporter:
    SUPPORTED_FORMATS = ['csv']

    ELECTRICITY_TEMPLATE = {
        'name': '电费账单',
        'description': '批量导入月度/日度用电记录',
        'required_columns': ['activity_date', 'amount'],
        'optional_columns': ['notes'],
        'defaults': {
            'category': 'electricity',
            'activity_type': 'grid_electricity'
        },
        'column_mapping': {
            '日期': 'activity_date',
            'date': 'activity_date',
            '用电量': 'amount',
            '度数': 'amount',
            'kwh': 'amount',
            '用电量(kWh)': 'amount',
            '备注': 'notes',
            'note': 'notes'
        }
    }

    FUEL_TEMPLATE = {
        'name': '加油记录',
        'description': '批量导入加油/燃料消费记录',
        'required_columns': ['activity_date', 'amount', 'activity_type'],
        'optional_columns': ['notes'],
        'defaults': {
            'category': 'transport'
        },
        'column_mapping': {
            '日期': 'activity_date',
            'date': 'activity_date',
            '加油量': 'amount',
            '升数': 'amount',
            '里程': 'amount',
            '公里': 'amount',
            'distance': 'amount',
            '燃油类型': 'activity_type',
            '交通方式': 'activity_type',
            'type': 'activity_type',
            '备注': 'notes',
            'note': 'notes'
        },
        'activity_type_mapping': {
            '汽油': 'car_gasoline',
            'gasoline': 'car_gasoline',
            'petrol': 'car_gasoline',
            '柴油': 'car_diesel',
            'diesel': 'car_diesel',
            '电动': 'car_electric',
            'electric': 'car_electric',
            '混动': 'car_hybrid',
            'hybrid': 'car_hybrid'
        }
    }

    GENERAL_TEMPLATE = {
        'name': '通用活动记录',
        'description': '批量导入各类活动数据',
        'required_columns': ['category', 'activity_type', 'activity_date', 'amount'],
        'optional_columns': ['notes'],
        'defaults': {},
        'column_mapping': {
            '类别': 'category',
            'category': 'category',
            '类型': 'activity_type',
            '活动类型': 'activity_type',
            'type': 'activity_type',
            '日期': 'activity_date',
            'date': 'activity_date',
            '数量': 'amount',
            'amount': 'amount',
            '数值': 'amount',
            '备注': 'notes',
            'note': 'notes'
        }
    }

    TEMPLATES = {
        'electricity': ELECTRICITY_TEMPLATE,
        'fuel': FUEL_TEMPLATE,
        'general': GENERAL_TEMPLATE
    }

    CATEGORY_MAPPING = {
        '交通': 'transport',
        '出行': 'transport',
        'transport': 'transport',
        '电力': 'electricity',
        '用电': 'electricity',
        'electricity': 'electricity',
        '饮食': 'food',
        '食物': 'food',
        'food': 'food',
        '购物': 'shopping',
        'shopping': 'shopping',
        '采暖': 'heating',
        '供暖': 'heating',
        'heating': 'heating',
        '水': 'water',
        '用水': 'water',
        'water': 'water',
        '垃圾': 'waste',
        '废弃物': 'waste',
        'waste': 'waste'
    }

    def __init__(self, data_manager: DataManager):
        self.dm = data_manager

    def list_templates(self) -> List[Dict]:
        result = []
        for key, template in self.TEMPLATES.items():
            result.append({
                'key': key,
                'name': template['name'],
                'description': template['description'],
                'required_columns': template['required_columns'],
                'optional_columns': template['optional_columns']
            })
        return result

    def generate_template_csv(self, template_key: str, output_path: str) -> bool:
        if template_key not in self.TEMPLATES:
            return False

        template = self.TEMPLATES[template_key]
        columns = list(template['required_columns']) + list(template['optional_columns'])

        sample_data = self._get_sample_data(template_key)

        try:
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in sample_data:
                    writer.writerow([row.get(col, '') for col in columns])
            return True
        except Exception:
            return False

    def _get_sample_data(self, template_key: str) -> List[Dict]:
        today = date.today().isoformat()
        if template_key == 'electricity':
            return [
                {'activity_date': today, 'amount': '156.5', 'notes': '本月家庭用电'},
                {'activity_date': '2026-05-01', 'amount': '142.0', 'notes': '上月用电'}
            ]
        elif template_key == 'fuel':
            return [
                {'activity_date': today, 'amount': '450', 'activity_type': '汽油', 'notes': '本月通勤里程(公里)'},
                {'activity_date': '2026-06-01', 'amount': '320', 'activity_type': '汽油', 'notes': '周末自驾'}
            ]
        else:
            return [
                {'category': '交通', 'activity_type': 'car_gasoline', 'activity_date': today, 'amount': '50', 'notes': '上下班'},
                {'category': '饮食', 'activity_type': 'beef', 'activity_date': today, 'amount': '2', 'notes': '午餐牛肉'},
                {'category': '购物', 'activity_type': 'clothing', 'activity_date': today, 'amount': '1', 'notes': '买T恤'}
            ]

    def import_csv(self, user_id: str, file_path: str,
                   template_key: str = None,
                   encoding: str = 'utf-8-sig') -> Tuple[int, List[Dict], List[str]]:
        if not os.path.exists(file_path):
            return 0, [], [f'文件不存在: {file_path}']

        template = None
        if template_key and template_key in self.TEMPLATES:
            template = self.TEMPLATES[template_key]

        try:
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk', newline='') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
            except Exception as e:
                return 0, [], [f'文件编码不支持: {e}']
        except Exception as e:
            return 0, [], [f'读取文件失败: {e}']

        if not rows:
            return 0, [], ['文件为空或格式不正确']

        errors = []
        activities = []
        skipped = 0

        for row_idx, row in enumerate(rows, start=2):
            try:
                activity = self._parse_row(row, template, row_idx)
                if activity:
                    activities.append(activity)
                else:
                    skipped += 1
            except ValueError as e:
                errors.append(f'第{row_idx}行: {e}')
                skipped += 1

        added = self.dm.bulk_add_activities(user_id, activities)

        if skipped > 0:
            errors.append(f'共跳过 {skipped} 条记录')

        return len(added), added, errors

    def _parse_row(self, row: Dict, template: Optional[Dict], row_num: int) -> Optional[Dict]:
        normalized = {}

        if template:
            mapping = template['column_mapping']
            for src_col, tgt_col in mapping.items():
                if src_col in row and row[src_col]:
                    normalized[tgt_col] = row[src_col].strip()
                elif tgt_col in row and row[tgt_col]:
                    normalized[tgt_col] = row[tgt_col].strip()

            for key, value in template.get('defaults', {}).items():
                if key not in normalized:
                    normalized[key] = value

            if 'activity_type_mapping' in template and 'activity_type' in normalized:
                at = normalized['activity_type']
                mapped = template['activity_type_mapping'].get(at)
                if mapped:
                    normalized['activity_type'] = mapped
        else:
            auto_template = None
            columns_lower = {k.lower(): v.strip() for k, v in row.items() if v and v.strip()}

            if 'category' in row and row['category']:
                normalized['category'] = self._normalize_category(row['category'].strip())
            elif '类别' in row and row['类别']:
                normalized['category'] = self._normalize_category(row['类别'].strip())

            for key in ['activity_type', 'activity_date', 'amount', 'notes',
                        '类型', '日期', '数量', '备注']:
                if key in row and row[key]:
                    tgt_key = self._map_column(key)
                    normalized[tgt_key] = row[key].strip()

        required = ['category', 'activity_type', 'activity_date', 'amount']
        missing = [r for r in required if r not in normalized or not normalized[r]]
        if missing:
            if template:
                req_names = ', '.join(template['required_columns'])
                raise ValueError(f'缺少必要列: {req_names}')
            else:
                raise ValueError(f'缺少必要字段: {", ".join(missing)}')

        try:
            normalized['amount'] = float(normalized['amount'])
        except (ValueError, TypeError):
            raise ValueError(f'数量格式无效: {normalized["amount"]}')

        if normalized['amount'] < 0:
            raise ValueError(f'数量不能为负数: {normalized["amount"]}')

        normalized['activity_date'] = self._normalize_date(normalized['activity_date'])
        if not normalized['activity_date']:
            raise ValueError(f'日期格式无效: {row.get("activity_date", row.get("日期", ""))}')

        normalized['category'] = self._normalize_category(normalized['category'])
        if not self._validate_category(normalized['category']):
            raise ValueError(f'无效的类别: {normalized["category"]}')

        if not self._validate_activity_type(normalized['category'], normalized['activity_type']):
            valid_types = [t['key'] for t in self.dm.get_activity_types(normalized['category'])]
            raise ValueError(f'无效的活动类型: {normalized["activity_type"]}, '
                           f'有效值: {", ".join(valid_types[:5])}{"..." if len(valid_types) > 5 else ""}')

        return normalized

    def _map_column(self, col: str) -> str:
        mapping = {
            '类别': 'category',
            '类型': 'activity_type',
            '活动类型': 'activity_type',
            '日期': 'activity_date',
            '数量': 'amount',
            '数值': 'amount',
            '备注': 'notes'
        }
        return mapping.get(col, col)

    def _normalize_category(self, category: str) -> str:
        if not category:
            return ''
        cat_lower = category.lower().strip()
        return self.CATEGORY_MAPPING.get(category.strip(),
                                         self.CATEGORY_MAPPING.get(cat_lower, category.strip()))

    def _validate_category(self, category: str) -> bool:
        return category in self.dm.get_categories()

    def _validate_activity_type(self, category: str, activity_type: str) -> bool:
        valid_types = [t['key'] for t in self.dm.get_activity_types(category)]
        return activity_type in valid_types

    def _normalize_date(self, date_str: str) -> Optional[str]:
        date_str = date_str.strip()
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y年%m月%d日',
            '%Y.%m.%d',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%Y%m%d'
        ]
        for fmt in formats:
            try:
                d = datetime.strptime(date_str, fmt)
                return d.date().isoformat()
            except ValueError:
                continue
        return None
