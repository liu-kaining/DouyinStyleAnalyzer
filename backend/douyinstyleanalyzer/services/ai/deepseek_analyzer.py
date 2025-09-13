"""
DeepSeek 大模型分析服务
用于分析博主风格和内容特点
"""

import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
from ...config import Config


class DeepSeekAnalyzer:
    """DeepSeek 大模型分析器"""
    
    def __init__(self):
        self.config = Config()
        self.api_key = getattr(self.config, 'DEEPSEEK_API_KEY', '')
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"
        
    def analyze_blogger_style(self, blogger_name: str, videos_data: List[Dict]) -> Dict:
        """
        分析博主风格
        
        Args:
            blogger_name: 博主名字
            videos_data: 视频数据列表，包含标题和转录文本
            
        Returns:
            分析结果字典
        """
        try:
            print(f"🤖 开始使用DeepSeek分析博主 {blogger_name} 的风格...")
            
            # 准备分析数据
            analysis_data = self._prepare_analysis_data(blogger_name, videos_data)
            
            # 构建分析提示词
            prompt = self._build_analysis_prompt(analysis_data)
            
            # 调用DeepSeek API
            response = self._call_deepseek_api(prompt)
            
            if response:
                # 解析响应
                analysis_result = self._parse_analysis_response(response)
                print(f"✅ DeepSeek分析完成")
                return analysis_result
            else:
                print(f"❌ DeepSeek分析失败")
                return self._get_default_analysis_result(blogger_name)
                
        except Exception as e:
            print(f"❌ DeepSeek分析出错: {e}")
            return self._get_default_analysis_result(blogger_name)
    
    def _prepare_analysis_data(self, blogger_name: str, videos_data: List[Dict]) -> Dict:
        """准备分析数据"""
        # 提取视频标题和转录文本
        titles = []
        transcripts = []
        
        for video in videos_data:
            if video.get('title'):
                titles.append(video['title'])
            if video.get('transcript'):
                transcripts.append(video['transcript'])
        
        return {
            'blogger_name': blogger_name,
            'total_videos': len(videos_data),
            'titles': titles,
            'transcripts': transcripts,
            'sample_titles': titles[:10],  # 取前10个标题作为样本
            'sample_transcripts': transcripts[:5]  # 取前5个转录文本作为样本
        }
    
    def _build_analysis_prompt(self, data: Dict) -> str:
        """构建分析提示词"""
        prompt = f"""
### **【竞品风格与策略深度解构】高级提示词**

**一、核心指令：**
请你扮演一位资深商业策略分析师与消费心理学专家。你的任务是对提供的文本内容进行一场极致深入的解构分析，最终产出一份可用于**深度模仿与战略超越**的竞品分析报告。报告需超越简单的风格归纳，必须揭示其底层的**内容架构、心理操纵机制、语言修辞系统及战略意图**。

**二、分析框架与必须涵盖的维度：**

1.  **战略定位与价值主张析出：**
    *   判定其在该内容生态中的独特角色（例如："反叛者"、"布道者"、"连接者"）。
    *   精准概括其向目标用户传递的核心价值主张。分析其如何同时满足用户的"功能需求"（如：学会写文案）和"情感需求"（如：获得认知优越感）。

2.  **内容架构的"公式化"拆解：**
    *   必须将其内容分解为可复用的结构性模块（例如："共情困境 → 错误示范 → 核心心法 → 三板斧 → 案例演绎 → 价值升华 → 互动引导"）。
    *   分析每个模块所运用的**心理学效应**（如：前景理论、不协调理论、JTBD理论）及其旨在实现的**具体用户心智影响**（如：建立信任、摧毁旧认知、提供价值感）。

3.  **语言修辞系统的精细解剖：**
    *   超越"生动有趣"的概括，需分类析出其具体的修辞手法词典。例如：
        *   **颠覆性比喻**：如何将抽象概念具象化。
        *   **情绪副词**：列举其最常用的情绪强化词（如：竟然、甚至、现载的），并分析其功能。
        *   **自创词汇**：识别并分析其创造新词的目的（建立话语体系、强化记忆点）。
        *   **对话体构建**：分析其如何通过人称代词和句式营造亲切感。

4.  **元理论支撑分析：**
    *   追溯其方法论背后可能存在的**经典营销理论、行为经济学原理或认知心理学模型**（如：FAB模型、JTBD、超级符号等），并解释他是如何将其"俗解"和"转化"为大众语言的。

5.  **可超越性分析与战略建议：**
    *   **模式创新建议**：基于分析，提出如何对其内容模式进行升级（例如：从"教案"升级为"剧本"或"工具"）。
    *   **内容深化方向**：指出其在理论深度或行业垂直度上的潜在短板，并提出强化建议。
    *   **人设差异化路径**：构思如何在模仿其有效结构的同时，通过更极致的"真实感"、"专业深度"或"互动模式"实现差异化超越。

**三、输出要求：**
*   **格式**：以结构化、带层级的Markdown格式输出。
*   **深度**：每一个论点都必须有来自原文的**具体引例**作为支撑。
*   **视角**：保持客观、冷静的战略分析视角，避免出现主观崇拜性语言。
*   **应用性**：报告的最终落脚点必须是"如何为其所用"，提供清晰的可操作策略。

---

**分析目标：**
博主名字：{data['blogger_name']}
分析视频数量：{data['total_videos']} 个

**视频标题样本：**
{json.dumps(data['sample_titles'], ensure_ascii=False, indent=2)}

**转录文本样本：**
{json.dumps(data['sample_transcripts'], ensure_ascii=False, indent=2)}

请基于以上内容，按照上述分析框架进行深度解构分析，并以Markdown格式返回分析结果。

要求：
1. 使用标准的Markdown语法
2. 每个分析维度使用二级标题（##）
3. 分析深入、专业，每个维度都要有具体的引例支撑
4. 提供可操作的战略建议
5. 保持结构清晰，便于阅读

请直接返回Markdown格式的分析报告，不要使用JSON格式。
"""
        return prompt
    
    def _call_deepseek_api(self, prompt: str) -> Optional[str]:
        """调用DeepSeek API"""
        if not self.api_key:
            print("⚠️ 未配置DeepSeek API Key，使用模拟分析")
            return self._get_mock_response()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        try:
            print("🔄 正在调用DeepSeek API...")
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"❌ DeepSeek API调用失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ DeepSeek API调用异常: {e}")
            return None
    
    def _get_mock_response(self) -> str:
        """获取模拟响应（用于测试）"""
        return """## 战略定位与价值主张析出

该博主在内容生态中扮演**"布道者"**角色，通过专业知识的通俗化表达，满足用户的功能需求（获取实用知识）和情感需求（获得认知优越感）。

### 核心价值主张
- **功能价值**：提供实用的营销知识和策略
- **情感价值**：让用户获得认知优越感和专业认同

## 内容架构的"公式化"拆解

内容结构遵循**"痛点共鸣→错误示范→核心方法论→案例验证→价值升华"**的经典模式，运用了前景理论和认知失调理论来影响用户心智。

### 内容模块分析
1. **痛点共鸣**：通过用户常见问题建立连接
2. **错误示范**：展示错误做法，制造认知冲突
3. **核心方法论**：提供解决方案和具体步骤
4. **案例验证**：用真实案例证明方法有效性
5. **价值升华**：将具体方法上升到理论高度

## 语言修辞系统的精细解剖

### 修辞手法词典
- **颠覆性比喻**：将抽象概念具象化，如"营销就像谈恋爱"
- **情绪副词**：频繁使用"竟然"、"甚至"、"现载的"等强化表达
- **自创词汇**：创造专业术语建立话语体系
- **对话体构建**：通过"你"、"我们"等人称代词营造亲切感

## 元理论支撑分析

其方法论背后体现了多个经典理论：

- **FAB模型**（特性-优势-利益）：将产品特性转化为用户利益
- **JTBD理论**（用户任务理论）：理解用户真实需求
- **前景理论**：利用损失厌恶心理
- **认知失调理论**：通过对比制造认知冲突

## 可超越性分析与战略建议

### 模式创新建议
1. **从"教案"升级为"剧本"**：增加互动元素和沉浸式体验
2. **内容深化**：引入更多行为经济学原理和心理学理论
3. **人设差异化**：通过更极致的真实感和专业深度实现超越

### 具体实施策略
- 增加用户参与度高的互动环节
- 提供更深入的理论分析和案例研究
- 建立独特的个人品牌和话语体系

## 总体评价与核心洞察

这是一个具有**明确战略意图**的知识分享型博主，其内容架构和语言修辞系统都经过精心设计，具备很强的可模仿性和超越潜力。

### 核心优势
- 结构化的内容框架
- 专业化的理论支撑
- 情感化的表达方式
- 实用化的价值输出

### 超越机会
通过更深入的理论研究、更丰富的案例分析、更创新的互动模式，可以在保持其有效结构的基础上实现差异化超越。"""
    
    def _parse_analysis_response(self, response: str) -> Dict:
        """解析分析响应"""
        try:
            # 直接返回markdown内容
            if response and response.strip():
                return {
                    "markdown": response.strip(),
                    "analysis_status": "completed"
                }
            else:
                return self._get_default_analysis_result("未知博主")
            
        except Exception as e:
            print(f"⚠️ 解析分析响应失败: {e}")
            return self._get_default_analysis_result("未知博主")
    
    def _get_default_analysis_result(self, blogger_name: str) -> Dict:
        """获取默认分析结果"""
        return {
            "markdown": f"""## 分析报告生成失败

很抱歉，{blogger_name}的分析报告生成过程中遇到了问题。

### 可能的原因
- API服务暂时不可用
- 网络连接问题
- 数据格式异常

### 建议操作
1. 检查网络连接
2. 稍后重试生成报告
3. 如问题持续，请联系技术支持

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*""",
            "analysis_status": "failed"
        }


def analyze_blogger_with_deepseek(blogger_name: str, videos_data: List[Dict]) -> Dict:
    """使用DeepSeek分析博主的便捷函数"""
    analyzer = DeepSeekAnalyzer()
    return analyzer.analyze_blogger_style(blogger_name, videos_data)
