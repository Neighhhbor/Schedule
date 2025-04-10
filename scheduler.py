import datetime
from collections import defaultdict, Counter

class Program:
    """表示一个演出节目"""
    def __init__(self, id, name, preferred_time_slots=None):
        self.id = id
        self.name = name
        self.preferred_time_slots = preferred_time_slots or []
        self.assigned_slots = []

class TimeSlot:
    """表示一个时间段"""
    def __init__(self, day, start_hour, end_hour):
        self.day = day
        self.start_hour = start_hour
        self.end_hour = end_hour
    
    def __repr__(self):
        return f"{self.day} {self.start_hour}:00-{self.end_hour}:00"
    
    def __eq__(self, other):
        return (self.day == other.day and 
                self.start_hour == other.start_hour and 
                self.end_hour == other.end_hour)
    
    def __hash__(self):
        return hash((self.day, self.start_hour, self.end_hour))

class Venue:
    """表示一个场地"""
    def __init__(self, name):
        self.name = name

class Schedule:
    """排练时间表"""
    def __init__(self):
        # 存储格式: {time_slot: {venue_name: program_id}}
        self.assignments = defaultdict(dict)
        self.venues = ["A", "B", "C"]
    
    def assign(self, time_slot, venue_name, program):
        """分配一个时间段的场地给特定节目"""
        self.assignments[time_slot][venue_name] = program
        program.assigned_slots.append((time_slot, venue_name))
    
    def is_venue_available(self, time_slot, venue_name):
        """检查某个时间段的某个场地是否可用"""
        return venue_name not in self.assignments[time_slot]
    
    def available_venues(self, time_slot):
        """返回某个时间段的所有可用场地"""
        return [v for v in self.venues if v not in self.assignments[time_slot]]
    
    def print_schedule(self):
        """打印排练时间表"""
        # 按天和时间排序
        sorted_slots = sorted(self.assignments.keys(), 
                              key=lambda x: (x.day, x.start_hour))
        
        for slot in sorted_slots:
            print(f"\n{slot}:")
            for venue in self.venues:
                if venue in self.assignments[slot]:
                    program = self.assignments[slot][venue]
                    print(f"  场地 {venue}: {program.name} (ID: {program.id})")
                else:
                    print(f"  场地 {venue}: 空闲")

class Scheduler:
    """排练调度器"""
    def __init__(self, time_slots, programs):
        self.time_slots = time_slots
        self.programs = programs
        self.schedule = Schedule()
    
    def calculate_conflicts(self):
        """计算每个时间段的冲突程度（有多少节目想要该时间段）"""
        conflicts = Counter()
        for program in self.programs:
            for slot in program.preferred_time_slots:
                conflicts[slot] += 1
        return conflicts
    
    def calculate_program_priorities(self, conflicts):
        """计算每个节目的优先级"""
        priorities = []
        # 统计每个节目已获得的资源量
        assigned_count = {program.id: len(program.assigned_slots) for program in self.programs}
        
        for program in self.programs:
            # 未满足的意向时间段数量
            unsatisfied = len([slot for slot in program.preferred_time_slots 
                              if not any(assigned[0] == slot for assigned in program.assigned_slots)])
            
            if unsatisfied == 0:
                continue
                
            # 优先级计算：冲突越少，已分配越少，优先级越高
            avg_conflict = sum(conflicts[slot] for slot in program.preferred_time_slots) / len(program.preferred_time_slots)
            priority = (1 / (avg_conflict + 0.1)) * (1 / (assigned_count[program.id] + 1))
            
            priorities.append((program, priority))
        
        # 按优先级降序排序
        return sorted(priorities, key=lambda x: x[1], reverse=True)
    
    def allocate(self):
        """进行资源分配"""
        # 持续分配直到无法再分配
        changes = True
        iteration = 0
        max_iterations = 10  # 限制迭代次数，防止无限循环
        
        while changes and iteration < max_iterations:
            changes = False
            conflicts = self.calculate_conflicts()
            program_priorities = self.calculate_program_priorities(conflicts)
            
            for program, _ in program_priorities:
                # 检查节目的每个意向时间段
                for slot in program.preferred_time_slots:
                    # 检查该时间段是否已为该节目分配
                    if any(assigned[0] == slot for assigned in program.assigned_slots):
                        continue
                    
                    # 检查是否有可用场地
                    available_venues = self.schedule.available_venues(slot)
                    if available_venues:
                        # 分配第一个可用场地
                        self.schedule.assign(slot, available_venues[0], program)
                        changes = True
                        break  # 为当前节目分配一个时间段后继续处理下一个节目
            
            iteration += 1
        
        return self.schedule

def create_weekly_time_slots(start_hour=9, end_hour=22):
    """创建一周的时间段列表"""
    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    slots = []
    
    for day in days:
        for hour in range(start_hour, end_hour):
            slots.append(TimeSlot(day, hour, hour+1))
    
    return slots

def main():
    # 创建一周的时间段
    time_slots = create_weekly_time_slots()
    
    # 创建示例节目
    programs = [
        Program(1, "舞蹈《春天》", [
            TimeSlot("周一", 14, 15), 
            TimeSlot("周二", 16, 17),
            TimeSlot("周四", 19, 20)
        ]),
        Program(2, "话剧《青春》", [
            TimeSlot("周一", 14, 15),
            TimeSlot("周三", 18, 19)
        ]),
        Program(3, "合唱《祖国》", [
            TimeSlot("周二", 16, 17),
            TimeSlot("周五", 17, 18)
        ]),
        Program(4, "独奏《梦想》", [
            TimeSlot("周四", 19, 20),
            TimeSlot("周六", 15, 16)
        ]),
        Program(5, "小品《生活》", [
            TimeSlot("周三", 18, 19),
            TimeSlot("周日", 14, 15)
        ])
    ]
    
    # 创建调度器并分配
    scheduler = Scheduler(time_slots, programs)
    final_schedule = scheduler.allocate()
    
    # 打印结果
    print("排练场地分配结果:")
    final_schedule.print_schedule()
    
    # 打印每个节目的分配情况
    print("\n节目分配情况:")
    for program in programs:
        if program.assigned_slots:
            print(f"{program.name}:")
            for slot, venue in program.assigned_slots:
                print(f"  {slot} 场地{venue}")
        else:
            print(f"{program.name}: 未分配到时间段")

if __name__ == "__main__":
    main() 