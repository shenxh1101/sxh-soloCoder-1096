import csv
import os
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from .data_manager import DataManager


class DataImporter:
    SUPPORTED_FORMATS = ['csv']

    FUEL_CONVERSION = {
        'car_gasoline': 0.10,
        'car_diesel': 0.085,
        'car_electric': 0.15,
        'car_hybrid': 0.07
    }

    ELECTRICITY_TEMPLATE = {
        'name': '电费账单',
        'description': '批量导入月度/日度用电记录 (用电量单位: kWh/度)',
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
            '千瓦时': 'amount',
            '用电量(kWh)': 'amount',
            '用电量(度)': 'amount',
            '备注': 'notes',
            'note': 'notes',
            '说明': 'notes'
        }
    }

    FUEL_TEMPLATE = {
        'name': '加油记录',
        'description': '批量导入加油/燃料消费记录 (支持升数或里程)',
        'required_columns': ['activity_date', 'amount', 'activity_type'],
        'optional_columns': ['amount_unit', 'notes'],
        'defaults': {
            'category': 'transport',
            'amount_unit': 'km'
        },
        'column_mapping': {
            '日期': 'activity_date',
            'date': 'activity_date',
            '加油量': 'amount',
            '升数': 'amount',
            '加油量(L)': 'amount',
            '加油量(升)': 'amount',
            '里程': 'amount',
            '公里': 'amount',
            '行驶里程': 'amount',
            'distance': 'amount',
            'km': 'amount',
            '单位': 'amount_unit',
            '计量单位': 'amount_unit',
            'unit': 'amount_unit',
            '燃油类型': 'activity_type',
            '交通方式': 'activity_type',
            '燃料类型': 'activity_type',
            'type': 'activity_type',
            '备注': 'notes',
            'note': 'notes',
            '说明': 'notes'
        },
        'activity_type_mapping': {
            '汽油': 'car_gasoline',
            'gasoline': 'car_gasoline',
            'petrol': 'car_gasoline',
            'gas': 'car_gasoline',
            '柴油': 'car_diesel',
            'diesel': 'car_diesel',
            '电动': 'car_electric',
            'electric': 'car_electric',
            'ev': 'car_electric',
            '混动': 'car_hybrid',
            'hybrid': 'car_hybrid',
            '摩托车': 'motorcycle',
            '公交': 'bus',
            '地铁': 'subway'
        },
        'unit_mapping': {
            '升': 'liters',
            'l': 'liters',
            'liter': 'liters',
            'liters': 'liters',
            '公里': 'km',
            'km': 'km',
            '千米': 'km',
            'kilometer': 'km',
            'kilometers': 'km'
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
                {'activity_date': today, 'amount': '45', 'activity_type': '汽油', 'amount_unit': '升', 'notes': '加油45升，约行驶600公里'},
                {'activity_date': '2026-06-05', 'amount': '320', 'activity_type': '汽油', 'amount_unit': '公里', 'notes': '周末自驾里程'},
                {'activity_date': '2026-06-10', 'amount': '38', 'activity_type': '柴油', 'amount_unit': '升', 'notes': '柴油车加油'}
            ]
        else:
            return [
                {'category': '交通', 'activity_type': 'car_gasoline', 'activity_date': today, 'amount': '50', 'notes': '上下班通勤'},
                {'category': '饮食', 'activity_type': 'beef', 'activity_date': today, 'amount': '2', 'notes': '午餐牛肉2份'},
                {'category': '购物', 'activity_type': 'clothing', 'activity_date': today, 'amount': '1', 'notes': '购买T恤1件'}
            ]

    def preview_csv(self, file_path: str, template_key: str = None,
                    encoding: str = 'utf-8-sig',
                    region: str = 'national_average') -> Dict:
        template_name = '自动检测'
        if template_key and template_key in self.TEMPLATES:
            template_name = self.TEMPLATES[template_key]['name']

        if not os.path.exists(file_path):
            return {
                'valid': False,
                'error': f'文件不存在: {file_path}',
                'total_rows': 0,
                'valid_rows': 0,
                'invalid_rows': 0,
                'skipped_rows': 0,
                'estimated_emission': 0,
                'template': template_name,
                'valid_details': [],
                'invalid_details': [],
                'skipped_details': [],
                'raw_rows': []
            }

        template = None
        if template_key and template_key in self.TEMPLATES:
            template = self.TEMPLATES[template_key]

        try:
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                fieldnames = reader.fieldnames or []
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk', newline='') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    fieldnames = reader.fieldnames or []
            except Exception as e:
                return {
                    'valid': False,
                    'error': f'文件编码不支持: {e}',
                    'total_rows': 0,
                    'valid_rows': 0,
                    'invalid_rows': 0,
                    'skipped_rows': 0,
                    'estimated_emission': 0,
                    'template': template_name,
                    'valid_details': [],
                    'invalid_details': [{'row': 0, 'reason': str(e)}],
                    'skipped_details': [],
                    'raw_rows': []
                }
        except Exception as e:
            return {
                'valid': False,
                'error': f'读取文件失败: {e}',
                'total_rows': 0,
                'valid_rows': 0,
                'invalid_rows': 0,
                'skipped_rows': 0,
                'estimated_emission': 0,
                'template': template_name,
                'valid_details': [],
                'invalid_details': [{'row': 0, 'reason': str(e)}],
                'skipped_details': [],
                'raw_rows': []
            }

        if not rows:
            return {
                'valid': True,
                'error': None,
                'total_rows': 0,
                'valid_rows': 0,
                'invalid_rows': 0,
                'skipped_rows': 0,
                'estimated_emission': 0,
                'template': template_name,
                'valid_details': [],
                'invalid_details': [],
                'skipped_details': [],
                'raw_rows': []
            }

        category_names = {
            'transport': '交通', 'electricity': '电力', 'food': '饮食',
            'shopping': '购物', 'heating': '采暖', 'water': '用水',
            'waste': '废弃物'
        }

        valid_details = []
        invalid_details = []
        skipped_details = []
        valid_rows_data = []
        total_emission = 0.0

        for row_idx, row in enumerate(rows, start=2):
            try:
                activity = self._parse_row(row, template, row_idx)
                if activity:
                    emission = self._calc_activity_emission(activity, region)
                    total_emission += emission
                    cat = activity.get('category', '')
                    act_type = activity.get('activity_type', '')
                    act_type_name = self._get_activity_type_name(cat, act_type)
                    cat_name = category_names.get(cat, cat)
                    valid_details.append({
                        'row': row_idx,
                        'date': activity.get('activity_date', ''),
                        'category': cat,
                        'category_name': cat_name,
                        'activity_type': act_type,
                        'type_name': act_type_name,
                        'amount': activity.get('amount', 0),
                        'emission': round(emission, 2),
                        'notes': activity.get('notes', ''),
                        'activity': activity
                    })
                    valid_rows_data.append(activity)
                else:
                    skipped_details.append({'row': row_idx, 'reason': '数据为空或跳过',
                                            'row_data': dict(row)})
            except ValueError as e:
                invalid_details.append({'row': row_idx, 'reason': str(e),
                                        'row_data': dict(row)})

        return {
            'valid': True,
            'error': None,
            'total_rows': len(rows),
            'valid_rows': len(valid_details),
            'invalid_rows': len(invalid_details),
            'skipped_rows': len(skipped_details),
            'estimated_emission': round(total_emission, 2),
            'template': template_name,
            'fieldnames': fieldnames,
            'valid_details': valid_details,
            'invalid_details': invalid_details,
            'skipped_details': skipped_details,
            'valid_activities': valid_rows_data,
            'raw_rows': rows
        }

    def export_failed_rows(self, file_path: str, invalid_details: List[Dict],
                           fieldnames: List[str] = None) -> bool:
        if not invalid_details:
            return False

        try:
            if fieldnames is None:
                fieldnames = ['row', 'reason']
                if invalid_details and 'row_data' in invalid_details[0]:
                    sample_row = invalid_details[0].get('row_data', {})
                    fieldnames = list(sample_row.keys()) + ['导入失败原因']
            else:
                fieldnames = list(fieldnames) + ['导入失败原因']

            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                for item in invalid_details:
                    row_data = dict(item.get('row_data', {}))
                    row_data['导入失败原因'] = item.get('reason', '')
                    writer.writerow(row_data)
            return True
        except Exception as e:
            print(f"导出失败行错误: {e}")
            return False

    def _calc_activity_emission(self, activity: Dict, region: str) -> float:
        from modules.calculator import CarbonCalculator
        calc = CarbonCalculator(self.dm)
        return calc.calculate_activity_emission(activity, region)

    def import_csv(self, user_id: str, file_path: str,
                   template_key: str = None,
                   encoding: str = 'utf-8-sig') -> Tuple[int, List[Dict], List[str], Dict]:
        template_name = '自动检测'
        if template_key and template_key in self.TEMPLATES:
            template_name = self.TEMPLATES[template_key]['name']

        if not os.path.exists(file_path):
            return 0, [], [f'文件不存在: {file_path}'], {
                'total_rows': 0, 'success_count': 0, 'failed_count': 0,
                'skipped_count': 0, 'template': template_name,
                'success_details': [], 'failed_details': [], 'skipped_details': []
            }

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
                return 0, [], [f'文件编码不支持: {e}'], {
                    'total_rows': 0, 'success_count': 0, 'failed_count': 0,
                    'skipped_count': 0, 'template': template_name,
                    'success_details': [], 'failed_details': [str(e)], 'skipped_details': []
                }
        except Exception as e:
            return 0, [], [f'读取文件失败: {e}'], {
                'total_rows': 0, 'success_count': 0, 'failed_count': 0,
                'skipped_count': 0, 'template': template_name,
                'success_details': [], 'failed_details': [str(e)], 'skipped_details': []
            }

        if not rows:
            return 0, [], ['文件为空或格式不正确'], {
                'total_rows': 0, 'success_count': 0, 'failed_count': 0,
                'skipped_count': 0, 'template': template_name,
                'success_details': [], 'failed_details': [], 'skipped_details': []
            }

        errors = []
        activities = []
        skipped_details = []
        success_details = []
        failed_details = []

        category_names = {
            'transport': '交通', 'electricity': '电力', 'food': '饮食',
            'shopping': '购物', 'heating': '采暖', 'water': '用水',
            'waste': '废弃物'
        }

        for row_idx, row in enumerate(rows, start=2):
            try:
                activity = self._parse_row(row, template, row_idx)
                if activity:
                    activities.append(activity)
                    cat = activity.get('category', '')
                    act_type = activity.get('activity_type', '')
                    act_type_name = self._get_activity_type_name(cat, act_type)
                    cat_name = category_names.get(cat, cat)
                    success_details.append({
                        'row': row_idx,
                        'date': activity.get('activity_date', ''),
                        'category': cat,
                        'category_name': cat_name,
                        'activity_type': act_type,
                        'type_name': act_type_name,
                        'amount': activity.get('amount', 0),
                        'activity': activity
                    })
                else:
                    skipped_details.append({'row': row_idx, 'reason': '数据为空或跳过'})
            except ValueError as e:
                failed_details.append({'row': row_idx, 'reason': str(e)})
                errors.append(f'第{row_idx}行: {e}')

        added = self.dm.bulk_add_activities(user_id, activities)

        summary = {
            'total_rows': len(rows),
            'success_count': len(added),
            'failed_count': len(failed_details),
            'skipped_count': len(skipped_details),
            'template': template_name,
            'success_details': success_details[:20],
            'failed_details': failed_details,
            'skipped_details': skipped_details,
            'total_emission': 0.0
        }

        return len(added), added, errors, summary

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

            if 'unit_mapping' in template and 'amount_unit' in normalized:
                unit_str = str(normalized['amount_unit']).lower().strip()
                mapped_unit = template['unit_mapping'].get(unit_str)
                if mapped_unit:
                    normalized['amount_unit_parsed'] = mapped_unit

            if 'activity_type_mapping' in template and 'activity_type' in normalized:
                at = normalized['activity_type']
                at_lower = at.lower().strip()
                mapped = template['activity_type_mapping'].get(at)
                if not mapped:
                    mapped = template['activity_type_mapping'].get(at_lower)
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

        if template and template.get('name') == '加油记录':
            amount_unit = normalized.get('amount_unit_parsed', normalized.get('amount_unit', 'km'))
            if amount_unit == 'liters':
                fuel_type = normalized['activity_type']
                if fuel_type in self.FUEL_CONVERSION:
                    conversion = self.FUEL_CONVERSION[fuel_type]
                    original_amount = normalized['amount']
                    if fuel_type == 'car_electric':
                        normalized['amount'] = round(original_amount * conversion, 2)
                        unit_note = f' [充电{original_amount:.1f}度 → 里程{normalized["amount"]:.0f}公里]'
                    else:
                        normalized['amount'] = round(original_amount / conversion, 2)
                        unit_note = f' [加油{original_amount:.1f}升 → 里程{normalized["amount"]:.0f}公里]'
                    existing_notes = normalized.get('notes', '')
                    normalized['notes'] = unit_note if not existing_notes else existing_notes + unit_note

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
        if category == 'electricity' and activity_type == 'grid_electricity':
            return True
        valid_types = [t['key'] for t in self.dm.get_activity_types(category)]
        return activity_type in valid_types

    def _get_activity_type_name(self, category: str, activity_type: str) -> str:
        if category == 'electricity' and activity_type == 'grid_electricity':
            return '家庭用电'
        types = self.dm.get_activity_types(category)
        for t in types:
            if t['key'] == activity_type:
                return t['name']
        return activity_type

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
