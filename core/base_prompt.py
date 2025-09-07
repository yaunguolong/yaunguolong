from langchain.prompts import PromptTemplate

CUSTOM_RAG_PROMPT = PromptTemplate.from_template("""
    你是一名专业的问答助手，请根据以下内容回答用户的问题。
    请确保你的答案来自文档，不要编造。
    如果文档中找不到答案，就说 "文档中没有相关信息"。
    
    问题：{question}
    
    文档内容：
    {context}
    
    答：""")

# 默认提示词模板
DEFAULT_PROMPTS = {
    "rag": CUSTOM_RAG_PROMPT,
    "rag_fusion": PromptTemplate.from_template("""
        你是一个专家，负责为给定的问题生成多个搜索查询。
        基于以下问题，生成5个不同的搜索查询，以帮助检索相关信息。
        
        原始问题：{question}
        
        生成的搜索查询：
        """),
    "multi": PromptTemplate.from_template("""
        你是一个专家，负责为给定的问题生成多个搜索查询。
        基于以下问题，生成5个不同的搜索查询，以帮助检索相关信息。
        
        原始问题：{question}
        
        生成的搜索查询：
        """),
    "decomposition": PromptTemplate.from_template("""
        将以下复杂问题分解为3-5个子问题，每个子问题应该能够独立回答：
        
        复杂问题：{question}
        
        子问题：
        """),
    "sub_question": PromptTemplate.from_template("""
        基于以下文档内容回答子问题：
        
        子问题：{sub_question}
        
        文档内容：
        {documents}
        
        答案：
        """),
    "final_answer": PromptTemplate.from_template("""
        基于以下子问题的答案，回答原始问题：
        
        原始问题：{question}
        
        子问题答案：
        {context}
        
        最终答案：
        """)
}

# 提示词配置
PROMPTS = {
    "DEFAULT_PROMPTS": DEFAULT_PROMPTS
}


def get_rag_prompt():
    """获取RAG提示词模板"""
    return DEFAULT_PROMPTS["rag"]
