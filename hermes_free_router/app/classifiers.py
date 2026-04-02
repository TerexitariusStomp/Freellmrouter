import re
from typing import List, Optional
from enum import Enum


class TaskType(str, Enum):
    GENERAL = "general"
    CODING = "coding"
    REASONING = "reasoning"
    VISION = "vision"
    LONG_CONTEXT = "long"
    FAST = "fast"


# Keywords for task classification
CODING_KEYWORDS = [
    r'\b(code|coding|program|programming|function|class|variable|loop|if|else|for|while)\b',
    r'\b(algorithm|debug|debugging|error|exception|syntax|compile|compile)\b',
    r'\b(python|javascript|java|c\+\+|ruby|php|swift|kotlin|go|rust)\b',
    r'\b(api|endpoint|rest|graphql|database|sql|query)\b',
    r'\b(framework|library|package|module|import|export)\b',
    r'\b(git|github|repository|commit|push|pull|merge)\b',
    r'\b(html|css|frontend|backend|fullstack)\b',
    r'\b(test|testing|unit test|integration test)\b',
    r'\b(refactor|refactoring|optimize|optimization)\b'
]

REASONING_KEYWORDS = [
    r'\b(solve|solution|answer|calculate|compute|math|mathematics)\b',
    r'\b(equation|formula|theorem|proof|logic|logical)\b',
    r'\b(statistics|probability|calculus|algebra|geometry)\b',
    r'\b(analyze|analysis|reason|reasoning|deduce|deduction)\b',
    r'\b(puzzle|riddle|brainstorm|brainstorming)\b',
    r'\b(if.*then|therefore|because|since|due to)\b'
]

VISION_KEYWORDS = [
    r'\b(image|picture|photo|visual|see|look|view)\b',
    r'\b(object|face|person|animal|scene|landscape)\b',
    r'\b(color|colour|shape|size|dimension)\b',
    r'\b(optical|camera|lens|photograph)\b',
    r'\b(detect|recognize|identify|classify|segment)\b'
]

LONG_CONTEXT_KEYWORDS = [
    r'\b(document|article|paper|essay|report|summarize|summary)\b',
    r'\b(book|chapter|page|paragraph|sentence|word)\b',
    r'\b(translate|translation|language|linguistic)\b',
    r'\b(context|contextual|background|history)\b',
    r'\b(long|lengthy|extensive|detailed|comprehensive)\b'
]

FAST_KEYWORDS = [
    r'\b(real.time|realtime|instant|immediate|quick|fast|speed)\b',
    r'\b(latency|response time|delay|lag)\b',
    r'\b(stream|streaming|live|realtime)\b'
]


def classify_task(prompt: str, max_tokens: Optional[int] = None, 
                 require_tool_calling: bool = False,
                 require_vision: bool = False,
                 require_json_mode: bool = False) -> TaskType:
    """
    Classify a task based on prompt text and requirements.
    
    Args:
        prompt: The user's prompt/input
        max_tokens: Maximum tokens requested (for long context detection)
        require_tool_calling: Whether tool calling is required
        require_vision: Whether vision capabilities are required
        require_json_mode: Whether JSON mode output is required
        
    Returns:
        TaskType enum value
    """
    prompt_lower = prompt.lower()
    
    # Check for explicit requirements first
    if require_vision:
        return TaskType.VISION
    
    if require_tool_calling:
        # Tool calling often associated with coding/tasks that need external interaction
        return TaskType.CODING
    
    # Score each task type based on keyword matches
    scores = {
        TaskType.CODING: 0,
        TaskType.REASONING: 0,
        TaskType.VISION: 0,
        TaskType.LONG_CONTEXT: 0,
        TaskType.FAST: 0,
        TaskType.GENERAL: 0  # Default fallback
    }
    
    # Check coding keywords
    for pattern in CODING_KEYWORDS:
        if re.search(pattern, prompt_lower):
            scores[TaskType.CODING] += 1
    
    # Check reasoning keywords
    for pattern in REASONING_KEYWORDS:
        if re.search(pattern, prompt_lower):
            scores[TaskType.REASONING] += 1
    
    # Check vision keywords
    for pattern in VISION_KEYWORDS:
        if re.search(pattern, prompt_lower):
            scores[TaskType.VISION] += 1
    
    # Check long context keywords
    for pattern in LONG_CONTEXT_KEYWORDS:
        if re.search(pattern, prompt_lower):
            scores[TaskType.LONG_CONTEXT] += 1
    
    # Check fast keywords
    for pattern in FAST_KEYWORDS:
        if re.search(pattern, prompt_lower):
            scores[TaskType.FAST] += 1
    
    # Adjust scores based on token count
    if max_tokens:
        if max_tokens > 8000:  # Very long context
            scores[TaskType.LONG_CONTEXT] += 2
        elif max_tokens > 4000:  # Moderately long context
            scores[TaskType.LONG_CONTEXT] += 1
    
    # Find the task type with the highest score
    max_score = max(scores.values())
    if max_score == 0:
        return TaskType.GENERAL
    
    # Get all task types with the max score
    top_tasks = [task for task, score in scores.items() if score == max_score]
    
    # Priority order for tie-breaking: vision > coding > reasoning > long_context > fast > general
    priority_order = [
        TaskType.VISION,
        TaskType.CODING,
        TaskType.REASONING,
        TaskType.LONG_CONTEXT,
        TaskType.FAST,
        TaskType.GENERAL
    ]
    
    for task in priority_order:
        if task in top_tasks:
            return task
    
    return TaskType.GENERAL  # Fallback


def get_task_description(task_type: TaskType) -> str:
    """Get a human-readable description of a task type."""
    descriptions = {
        TaskType.GENERAL: "General conversation and Q&A",
        TaskType.CODING: "Code generation, debugging, and development tasks",
        TaskType.REASONING: "Mathematical, logical, and analytical reasoning",
        TaskType.VISION: "Image understanding and visual tasks",
        TaskType.LONG_CONTEXT: "Document processing, summarization, and long-form content",
        TaskType.FAST: "Real-time or low-latency applications"
    }
    return descriptions.get(task_type, "Unknown task type")