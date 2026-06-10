from typing import List, Dict, Tuple


class Visualizer:
    COLOR_BLOCKS = ['█', '▓', '▒', '░', '■', '◆', '●', '▲', '▼', '★', '✦', '◉']
    COLOR_GRAYSCALE = ['█', '▓', '▒', '░', '□']

    PIE_SYMBOLS = ['#', '@', '*', '+', '=', '-', '.', '%', '&', '~', '^', '$']

    @staticmethod
    def ascii_pie_chart(data: List[Dict], title: str = '', width: int = 50,
                        height: int = 22, show_legend: bool = True) -> str:
        if not data:
            return '暂无数据\n'

        lines = []
        if title:
            lines.append(f'\n  {title}')
            lines.append('  ' + '─' * len(title))

        total = sum(item.get('emission', item.get('value', 0)) for item in data)
        if total <= 0:
            return '  数据总量为零，无法生成饼图\n'

        radius = min(width // 2, height) - 2
        center_x = radius + 2
        center_y = radius + 1

        pie = [[' ' for _ in range(width)] for _ in range(2 * radius + 2)]

        start_angle = -90
        for idx, item in enumerate(data):
            value = item.get('emission', item.get('value', 0))
            percentage = value / total
            sweep_angle = percentage * 360

            symbol = Visualizer.PIE_SYMBOLS[idx % len(Visualizer.PIE_SYMBOLS)]

            for y in range(2 * radius + 1):
                for x in range(2 * radius + 1):
                    dx = x - radius
                    dy = y - radius
                    dist_sq = dx * dx + dy * dy
                    if dist_sq <= radius * radius and dist_sq >= (radius // 3) * (radius // 3):
                        angle = Visualizer._calculate_angle(dx, dy)
                        if start_angle <= angle < start_angle + sweep_angle or \
                           (start_angle + sweep_angle > 270 and angle < start_angle + sweep_angle - 360):
                            pie[y + 1][x + 2] = symbol

            start_angle += sweep_angle

        for row in pie:
            lines.append('  ' + ''.join(row))

        if show_legend:
            lines.append('')
            max_name_len = max(len(item.get('category_name', item.get('type_name', item.get('name', str(i)))))
                               for i, item in enumerate(data))
            for idx, item in enumerate(data):
                value = item.get('emission', item.get('value', 0))
                percentage = round(value / total * 100, 1)
                symbol = Visualizer.PIE_SYMBOLS[idx % len(Visualizer.PIE_SYMBOLS)]
                name = item.get('category_name', item.get('type_name', item.get('name', str(idx))))
                lines.append(f'  {symbol} {name.ljust(max_name_len)}  {value:>8.2f} kg  ({percentage:>5.1f}%)')

        return '\n'.join(lines) + '\n'

    @staticmethod
    def _calculate_angle(dx: int, dy: int) -> float:
        import math
        angle = math.degrees(math.atan2(dy, dx))
        return angle

    @staticmethod
    def ascii_bar_chart(data: List[Dict], title: str = '', width: int = 60,
                        value_key: str = 'emission', label_key: str = 'category_name',
                        sort_desc: bool = True) -> str:
        if not data:
            return '暂无数据\n'

        if sort_desc:
            data = sorted(data, key=lambda x: x.get(value_key, 0), reverse=True)

        lines = []
        if title:
            lines.append(f'\n  {title}')
            lines.append('  ' + '=' * (width + 20))

        max_value = max(item.get(value_key, 0) for item in data)
        if max_value <= 0:
            max_value = 1

        max_label_len = min(max(len(str(item.get(label_key, ''))) for item in data), 12)
        bar_max_width = width - max_label_len - 15

        lines.append('')
        for item in data:
            label = str(item.get(label_key, ''))[:max_label_len].ljust(max_label_len)
            value = item.get(value_key, 0)
            bar_len = int(bar_max_width * value / max_value)
            bar = '█' * bar_len
            percentage = (value / max_value * 100) if max_value > 0 else 0
            lines.append(f'  {label} │{bar.ljust(bar_max_width)}│ {value:>7.2f} ({percentage:>5.1f}%)')

        lines.append('  ' + ' ' * max_label_len + ' └' + '─' * bar_max_width + '┘')
        lines.append('')

        return '\n'.join(lines) + '\n'

    @staticmethod
    def ascii_line_chart(trend_data: Dict, title: str = '',
                         width: int = 70, height: int = 14) -> str:
        labels = trend_data.get('labels', [])
        values = trend_data.get('values', [])
        benchmark = trend_data.get('benchmark', 0)

        if not values or not labels:
            return '暂无数据\n'

        lines = []
        if title:
            lines.append(f'\n  {title}')

        all_values = list(values)
        if benchmark > 0:
            all_values.append(benchmark)

        max_val = max(all_values) * 1.1 if max(all_values) > 0 else 1
        min_val = min(min(all_values) * 0.9, 0)
        value_range = max_val - min_val

        if value_range == 0:
            value_range = 1

        plot_width = width - 12
        plot_height = height

        grid = [[' ' for _ in range(plot_width)] for _ in range(plot_height)]

        if benchmark > 0:
            bench_y = plot_height - 1 - int((benchmark - min_val) / value_range * (plot_height - 1))
            if 0 <= bench_y < plot_height:
                for x in range(plot_width):
                    grid[bench_y][x] = '─'

        n_points = len(values)
        x_coords = []
        y_coords = []

        for i in range(n_points):
            x = int(i / max(n_points - 1, 1) * (plot_width - 1))
            y = plot_height - 1 - int((values[i] - min_val) / value_range * (plot_height - 1))
            x_coords.append(x)
            y_coords.append(y)

        for i in range(n_points - 1):
            Visualizer._draw_line(grid, x_coords[i], y_coords[i],
                                  x_coords[i + 1], y_coords[i + 1])

        for i in range(n_points):
            x, y = x_coords[i], y_coords[i]
            if 0 <= y < plot_height and 0 <= x < plot_width:
                grid[y][x] = '●'

        lines.append('')
        y_label_width = 8
        for row_idx in range(plot_height):
            value = max_val - (row_idx / (plot_height - 1)) * value_range
            if row_idx == 0 or row_idx == plot_height - 1 or row_idx == plot_height // 2:
                y_label = f'{value:>6.1f} '
            else:
                y_label = '       '
            row_str = ''.join(grid[row_idx])
            lines.append(f'  {y_label}│{row_str}│')

        lines.append('  ' + ' ' * y_label_width + '└' + '─' * plot_width + '┘')

        x_labels = [' ' * plot_width]
        label_str = list(' ' * plot_width)
        for i, label in enumerate(labels):
            x = int(i / max(n_points - 1, 1) * (plot_width - 1))
            start_idx = max(0, x - len(label) // 2)
            for j, ch in enumerate(label):
                if start_idx + j < plot_width:
                    label_str[start_idx + j] = ch
        lines.append('  ' + ' ' * y_label_width + ' ' + ''.join(label_str))

        legend_items = []
        legend_items.append('● 排放数据')
        if benchmark > 0:
            legend_items.append(f'─ 中国平均({benchmark:.1f}kg)')
        lines.append('')
        lines.append('  ' + '  '.join(legend_items))
        lines.append('')

        return '\n'.join(lines) + '\n'

    @staticmethod
    def _draw_line(grid: List[List[str]], x0: int, y0: int, x1: int, y1: int) -> None:
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            if 0 <= y0 < len(grid) and 0 <= x0 < len(grid[0]):
                if grid[y0][x0] == ' ':
                    grid[y0][x0] = '·'
                elif grid[y0][x0] == '─':
                    grid[y0][x0] = '┼'

            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    @staticmethod
    def progress_bar(current: float, target: float, width: int = 40,
                     show_percent: bool = True) -> str:
        if target <= 0:
            return '[目标值无效]'

        ratio = current / target
        ratio = max(0, min(ratio, 2))

        filled = int(width * min(ratio, 1))
        bar = '█' * filled + '░' * (width - filled)

        if ratio >= 1:
            result = f'[{bar}] ✓ 已达标'
        else:
            result = f'[{bar}]'

        if show_percent:
            percent = ratio * 100
            result += f' {percent:>5.1f}%'

        return result

    @staticmethod
    def progress_card(title: str, current: float, target: float,
                      unit: str = 'kg', width: int = 45) -> str:
        lines = []
        lines.append(f'  ┌{"─" * (width - 2)}┐')
        lines.append(f'  │ {title.ljust(width - 4)} │')
        lines.append(f'  ├{"─" * (width - 2)}┤')
        lines.append(f'  │  当前: {current:>8.2f} {unit}'.ljust(width - 1) + ' │')
        lines.append(f'  │  目标: {target:>8.2f} {unit}'.ljust(width - 1) + ' │')

        diff = target - current
        if diff >= 0:
            diff_str = f'  │  剩余: {diff:>8.2f} {unit} ✓'.ljust(width - 1) + ' │'
        else:
            diff_str = f'  │  超出: {abs(diff):>8.2f} {unit} ✗'.ljust(width - 1) + ' │'
        lines.append(diff_str)

        lines.append(f'  │ {" " * (width - 4)} │')
        bar = Visualizer.progress_bar(current, target, width - 6, show_percent=True)
        lines.append(f'  │  {bar.ljust(width - 6)} │')
        lines.append(f'  └{"─" * (width - 2)}┘')
        lines.append('')

        return '\n'.join(lines)

    @staticmethod
    def comparison_card(comparison: Dict, title: str = '与平均水平对比',
                        width: int = 50) -> str:
        lines = []
        lines.append(f'\n  ╔{"═" * (width - 2)}╗')
        lines.append(f'  ║ {title.center(width - 4)} ║')
        lines.append(f'  ╠{"═" * (width - 2)}╣')

        period = comparison.get('period', 'monthly')
        period_names = {'daily': '每日', 'weekly': '每周', 'monthly': '每月', 'yearly': '每年'}
        period_name = period_names.get(period, period)

        user_val = comparison.get('user_emission', 0)
        items = [
            ('您的排放', user_val, None),
            ('中国平均', comparison.get('china_average', 0), comparison.get('vs_china_percent', 0)),
            ('全球平均', comparison.get('global_average', 0), comparison.get('vs_global_percent', 0)),
            ('欧盟平均', comparison.get('eu_average', 0), comparison.get('vs_eu_percent', 0))
        ]

        max_val = max(v for _, v, _ in items) or 1

        for name, value, vs_percent in items:
            bar_len = int((width - 22) * value / max_val)
            bar = '█' * bar_len
            if vs_percent is None:
                tag = '← 您'
            else:
                if vs_percent > 0:
                    tag = f'↑{vs_percent:.0f}%'
                elif vs_percent < 0:
                    tag = f'↓{abs(vs_percent):.0f}%'
                else:
                    tag = '持平'
            lines.append(f'  ║ {name:<8} {value:>7.1f} kg {bar:<20} {tag:>6} ║')

        lines.append(f'  ╚{"═" * (width - 2)}╝')
        lines.append('')

        return '\n'.join(lines)

    @staticmethod
    def header(title: str, width: int = 60) -> str:
        lines = []
        lines.append('')
        lines.append('  ╔' + '═' * (width - 2) + '╗')
        lines.append('  ║' + title.center(width - 2) + '║')
        lines.append('  ╚' + '═' * (width - 2) + '╝')
        return '\n'.join(lines)

    @staticmethod
    def section(title: str, width: int = 60) -> str:
        return f'\n  ┌─ {title} ' + '─' * max(0, width - len(title) - 5) + '┐\n'
