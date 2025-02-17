import tkinter as tk
from tkinter import filedialog, simpledialog
from collections import defaultdict
import subprocess
import threading
import math


class FourOptionDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="请选择操作:").grid(row=0, column=0, columnspan=4)
        self.result = None
        return None

    def buttonbox(self):
        box = tk.Frame(self)

        b1 = tk.Button(box, text="选代码", width=10, command=lambda: self.ok(1))
        b1.pack(side=tk.LEFT, padx=5, pady=5)
        b2 = tk.Button(box, text="输入代码", width=10, command=lambda: self.ok(2))
        b2.pack(side=tk.LEFT, padx=5, pady=5)
        b3 = tk.Button(box, text="查看保存的代码", width=15, command=lambda: self.ok(3))
        b3.pack(side=tk.LEFT, padx=5, pady=5)
        b4 = tk.Button(box, text="不修改退出", width=10, command=lambda: self.ok(4))
        b4.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def ok(self, choice):
        self.result = choice
        self.destroy()


# 全局变量
graph = defaultdict(list)
nodes = []
node_names = {}
node_labels = {}
node_files = {}  # 存储每个节点对应的文件或代码
current_dragging = None
start_node = None
line = None
# 存储每条线对应的起始节点和结束节点
node_lines = defaultdict(list)
# 距离阈值，可根据需要调整
DISTANCE_THRESHOLD = 100
# 扩大的选中范围阈值
SELECTION_THRESHOLD = 80


# 拓扑排序函数
def topological_sort(graph):
    in_degree = defaultdict(int)
    for node in graph:
        for neighbor in graph[node]:
            in_degree[neighbor] += 1

    queue = [node for node in graph if in_degree[node] == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(graph):
        raise ValueError("Graph contains a cycle, cannot perform topological sort.")

    return result


# 执行文件函数
def execute_file(file):
    try:
        print(f"Executing {file}...")
        process = subprocess.Popen(['python', file])
        # 等待进程完成
        process.wait()
        if process.returncode == 0:
            print(f"{file} executed successfully.")
        else:
            print(f"Error executing {file}: Return code {process.returncode}")
    except Exception as e:
        print(f"Error executing {file}: {e}")


# 执行所有文件函数
def execute_all_files():
    try:
        execution_order = topological_sort(graph)
        print("Execution order:", execution_order)
        for file in execution_order:
            # 创建线程来执行每个文件
            thread = threading.Thread(target=execute_file, args=(file,))
            thread.start()
            # 等待线程完成
            thread.join()
    except ValueError as e:
        print(e)


# 自定义查找在指定范围内的节点
def find_node_in_range(x, y):
    for node in nodes:
        x1, y1, x2, y2 = canvas.coords(node)
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        if dist <= SELECTION_THRESHOLD:
            return node
    return None


# 右键点击节点的处理函数
def on_right_click(event):
    node = find_node_in_range(event.x, event.y)
    if node:
        dialog = FourOptionDialog(root, title="选择操作")
        choice = dialog.result
        if choice == 1:
            file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
            if file_path:
                node_files[node] = file_path
                node_names[node] = file_path
                print(f"节点 {node} 关联文件: {file_path}")
        elif choice == 2:
            code = simpledialog.askstring("输入代码", "请输入 Python 代码：")
            if code:
                # 这里可以将代码保存到临时文件，再执行
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code)
                node_files[node] = f.name
                node_names[node] = f.name
                print(f"节点 {node} 关联代码文件: {f.name}")
        elif choice == 3:
            file = node_files.get(node)
            if file:
                try:
                    with open(file, 'r') as f:
                        code_content = f.read()
                        print(f"节点 {node} 保存的代码内容:\n{code_content}")
                except Exception as e:
                    print(f"读取代码文件出错: {e}")
            else:
                print(f"节点 {node} 没有保存代码。")


# 创建节点函数
def create_node():
    global nodes, node_names, node_labels
    node_id = len(nodes) + 1
    node_name = f"script{node_id}.py"
    new_node = canvas.create_oval(50, 50, 100, 100, fill="blue")
    nodes.append(new_node)
    node_names[new_node] = node_name
    node_files[new_node] = None  # 初始化节点对应的文件或代码
    # 创建节点标号文本
    label = canvas.create_text(75, 75, text=str(node_id), fill="white")
    node_labels[new_node] = label
    canvas.tag_bind(new_node, "<ButtonPress-2>", start_drag)
    canvas.tag_bind(new_node, "<B2-Motion>", drag)
    canvas.tag_bind(new_node, "<ButtonRelease-2>", end_drag)
    canvas.tag_bind(new_node, "<ButtonPress-1>", start_connect)
    canvas.tag_bind(new_node, "<B1-Motion>", draw_line)
    canvas.tag_bind(new_node, "<ButtonRelease-1>", end_connect)
    canvas.tag_bind(new_node, "<ButtonPress-3>", on_right_click)  # 绑定右键点击事件


# 开始拖动节点
def start_drag(event):
    global current_dragging
    current_dragging = find_node_in_range(event.x, event.y)


# 更新与节点相连的线的坐标
def update_lines(node):
    for line_info in node_lines[node]:
        line_id, start_node, end_node = line_info
        x1, y1 = canvas.coords(start_node)[0] + 25, canvas.coords(start_node)[1] + 25
        x2, y2 = canvas.coords(end_node)[0] + 25, canvas.coords(end_node)[1] + 25
        canvas.coords(line_id, x1, y1, x2, y2)


# 拖动节点
def drag(event):
    global current_dragging
    if current_dragging:
        x, y = event.x, event.y
        canvas.coords(current_dragging, x - 25, y - 25, x + 25, y + 25)
        # 同时移动节点标号
        label = node_labels[current_dragging]
        canvas.coords(label, x, y)
        # 更新与当前拖动节点相连的线的坐标
        update_lines(current_dragging)


# 结束拖动节点
def end_drag(event):
    global current_dragging
    current_dragging = None


# 开始建立依赖关系
def start_connect(event):
    global start_node, line
    start_node = find_node_in_range(event.x, event.y)
    if start_node:
        x1, y1 = canvas.coords(start_node)[0] + 25, canvas.coords(start_node)[1] + 25
        line = canvas.create_line(x1, y1, x1, y1, arrow=tk.LAST)


# 绘制连线
def draw_line(event):
    global line, start_node
    if start_node:
        x1, y1 = canvas.coords(start_node)[0] + 25, canvas.coords(start_node)[1] + 25
        x2, y2 = event.x, event.y
        canvas.coords(line, x1, y1, x2, y2)


# 计算两点之间的距离
def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# 结束建立依赖关系
def end_connect(event):
    global start_node, line
    if start_node:
        min_distance = float('inf')
        closest_node = None
        mouse_x, mouse_y = event.x, event.y
        # 遍历所有节点，找出最近的节点
        for node in nodes:
            if node != start_node:
                x, y = canvas.coords(node)[0] + 25, canvas.coords(node)[1] + 25
                dist = distance(mouse_x, mouse_y, x, y)
                if dist < min_distance:
                    min_distance = dist
                    closest_node = node
        # 如果最近节点在距离阈值内，则建立连接
        if closest_node and min_distance <= DISTANCE_THRESHOLD:
            start_file = node_names[start_node]
            end_file = node_names[closest_node]
            graph[start_file].append(end_file)
            x1, y1 = canvas.coords(start_node)[0] + 25, canvas.coords(start_node)[1] + 25
            x2, y2 = canvas.coords(closest_node)[0] + 25, canvas.coords(closest_node)[1] + 25
            canvas.coords(line, x1, y1, x2, y2)
            # 记录线与节点的关联
            node_lines[start_node].append([line, start_node, closest_node])
            node_lines[closest_node].append([line, start_node, closest_node])
        else:
            canvas.delete(line)
        start_node = None
        line = None


# 创建主窗口
root = tk.Tk()
root.title("Task Dependency Graph")

# 创建画布
canvas = tk.Canvas(root, width=800, height=600)
canvas.pack()

# 创建按钮
create_button = tk.Button(root, text="Create Node", command=create_node)
create_button.pack()

execute_button = tk.Button(root, text="Execute All Files", command=execute_all_files)
execute_button.pack()

# 运行主循环
root.mainloop()