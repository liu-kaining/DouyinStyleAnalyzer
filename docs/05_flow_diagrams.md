# 流程图设计文档

## 5.1 系统整体流程图

```plantuml
@startuml
!theme plain
title DouyinStyleAnalyzer 系统整体流程

actor User as "用户"
participant "前端界面" as Frontend
participant "API网关" as Gateway
participant "任务管理器" as TaskManager
participant "视频采集器" as Scraper
participant "语音识别器" as Transcriber
participant "数据库" as Database
participant "文件存储" as Storage

User -> Frontend: 输入博主主页URL
Frontend -> Gateway: POST /api/v1/tasks
Gateway -> TaskManager: 创建分析任务
TaskManager -> Database: 保存任务信息
TaskManager -> Scraper: 启动视频采集

note over Scraper: 1. 打开浏览器\n2. 引导用户登录\n3. 自动滚动采集
Scraper -> Scraper: 采集视频列表
Scraper -> TaskManager: 返回视频数据
TaskManager -> Database: 更新任务进度

loop 对每个视频
    TaskManager -> Transcriber: 下载音频
    Transcriber -> Storage: 保存音频文件
    Transcriber -> Transcriber: 语音转文字
    Transcriber -> TaskManager: 返回转录结果
    TaskManager -> Database: 更新视频数据
end

TaskManager -> Storage: 生成JSON结果文件
TaskManager -> Database: 标记任务完成
TaskManager -> Frontend: 推送完成通知
Frontend -> User: 显示完成状态
User -> Frontend: 下载结果文件
Frontend -> Gateway: GET /api/v1/tasks/{id}/download
Gateway -> Storage: 返回文件下载

@enduml
```

## 5.2 任务处理详细流程图

```plantuml
@startuml
!theme plain
title 任务处理详细流程

start

:用户提交分析任务;
:验证URL格式;
if (URL有效?) then (是)
    :检查用户配额;
    if (配额充足?) then (是)
        :创建任务记录;
        :状态设为pending;
        :启动异步处理;
        
        :打开Selenium浏览器;
        :引导用户登录抖音;
        if (登录成功?) then (是)
            :访问博主主页;
            :自动滚动采集视频;
            :提取视频标题和URL;
            :状态更新为running;
            
            :初始化Whisper模型;
            repeat
                :下载视频音频;
                :语音转文字;
                :保存转录结果;
                :更新进度;
            repeat while (还有视频?) is (是)
            
            :生成JSON结果文件;
            :状态设为completed;
            :清理临时文件;
        else (否)
            :状态设为failed;
            :记录错误信息;
        endif
    else (否)
        :返回配额不足错误;
    endif
else (否)
    :返回URL格式错误;
endif

stop

@enduml
```

## 5.3 错误处理流程图

```plantuml
@startuml
!theme plain
title 错误处理流程

start

:执行任务步骤;
if (步骤成功?) then (是)
    :继续下一步;
else (否)
    :记录错误类型;
    
    if (网络错误?) then (是)
        :等待重试;
        :重试次数 < 3?;
        if (是) then (是)
            :重新执行步骤;
        else (否)
            :标记任务失败;
        endif
    elseif (反爬虫检测?) then (是)
        :等待更长时间;
        :更换User-Agent;
        :重新执行步骤;
    elseif (资源不足?) then (是)
        :暂停任务;
        :等待资源释放;
        :恢复任务;
    else (其他错误)
        :记录详细错误;
        :标记任务失败;
    endif
endif

stop

@enduml
```

## 5.4 数据流转图

```plantuml
@startuml
!theme plain
title 数据流转图

package "输入层" {
    [用户输入URL]
    [任务配置参数]
}

package "处理层" {
    [视频列表数据]
    [音频文件]
    [转录文本]
}

package "输出层" {
    [结构化JSON]
    [下载文件]
    [API响应]
}

package "存储层" {
    database "任务数据库" as DB
    folder "音频文件" as Audio
    folder "结果文件" as Result
}

[用户输入URL] --> [视频列表数据]
[任务配置参数] --> [视频列表数据]
[视频列表数据] --> [音频文件]
[音频文件] --> [转录文本]
[转录文本] --> [结构化JSON]
[结构化JSON] --> [下载文件]
[结构化JSON] --> [API响应]

[视频列表数据] --> DB
[音频文件] --> Audio
[结构化JSON] --> Result

@enduml
```

## 5.5 系统架构组件图

```plantuml
@startuml
!theme plain
title 系统架构组件图

package "前端层" {
    [Web界面]
    [任务监控]
    [文件下载]
}

package "API层" {
    [认证服务]
    [任务管理API]
    [数据下载API]
    [系统状态API]
}

package "业务层" {
    [用户管理服务]
    [任务调度服务]
    [视频采集服务]
    [语音识别服务]
}

package "数据层" {
    [用户数据库]
    [任务数据库]
    [文件存储]
    [缓存系统]
}

package "外部服务" {
    [Selenium浏览器]
    [yt-dlp下载器]
    [Faster-Whisper]
    [抖音平台]
}

[Web界面] --> [认证服务]
[任务监控] --> [任务管理API]
[文件下载] --> [数据下载API]

[认证服务] --> [用户管理服务]
[任务管理API] --> [任务调度服务]
[数据下载API] --> [文件存储]

[任务调度服务] --> [视频采集服务]
[任务调度服务] --> [语音识别服务]

[视频采集服务] --> [Selenium浏览器]
[视频采集服务] --> [抖音平台]
[语音识别服务] --> [yt-dlp下载器]
[语音识别服务] --> [Faster-Whisper]

[用户管理服务] --> [用户数据库]
[任务调度服务] --> [任务数据库]
[语音识别服务] --> [文件存储]
[任务调度服务] --> [缓存系统]

@enduml
```

## 5.6 用户交互流程图

```plantuml
@startuml
!theme plain
title 用户交互流程

actor User as "用户"
participant "Web界面" as UI
participant "后端服务" as Backend
participant "任务队列" as Queue

User -> UI: 访问系统
UI -> Backend: 检查登录状态
Backend -> UI: 返回用户信息
UI -> User: 显示主界面

User -> UI: 输入博主URL
UI -> Backend: 提交分析任务
Backend -> Queue: 创建任务
Queue -> Backend: 返回任务ID
Backend -> UI: 返回任务信息
UI -> User: 显示任务状态

loop 任务执行期间
    User -> UI: 刷新页面
    UI -> Backend: 查询任务状态
    Backend -> Queue: 获取任务进度
    Queue -> Backend: 返回进度信息
    Backend -> UI: 返回状态更新
    UI -> User: 显示进度条
end

Queue -> Backend: 任务完成通知
Backend -> UI: 推送完成消息
UI -> User: 显示完成状态

User -> UI: 点击下载
UI -> Backend: 请求下载文件
Backend -> UI: 返回文件流
UI -> User: 开始下载

@enduml
```

## 5.7 系统监控流程图

```plantuml
@startuml
!theme plain
title 系统监控流程

participant "监控服务" as Monitor
participant "任务管理器" as TaskManager
participant "资源监控" as ResourceMonitor
participant "告警系统" as Alert

Monitor -> TaskManager: 查询任务状态
TaskManager -> Monitor: 返回任务信息
Monitor -> ResourceMonitor: 查询系统资源
ResourceMonitor -> Monitor: 返回资源使用情况

if (资源使用率 > 80%?) then (是)
    Monitor -> Alert: 发送资源告警
    Alert -> Monitor: 确认告警
else (否)
    :继续监控;
endif

if (任务失败率 > 10%?) then (是)
    Monitor -> Alert: 发送任务告警
    Alert -> Monitor: 确认告警
else (否)
    :继续监控;
endif

if (系统响应时间 > 5s?) then (是)
    Monitor -> Alert: 发送性能告警
    Alert -> Monitor: 确认告警
else (否)
    :继续监控;
endif

Monitor -> Monitor: 记录监控数据
Monitor -> Monitor: 生成监控报告

@enduml
```
