# Langfuse Observability Examples

Este documento mostra exemplos dos traces que agora aparecem no Langfuse com o sistema de extração de metadados.

## Traces de Extração de Metadados

### 1. Trace Principal: `metadata_extraction`
**Span Principal:** Extração completa de metadados de um documento

**Inputs:**
- `content`: Conteúdo do documento processado pelo LlamaParse
- `url`: URL do documento original

**Outputs:**
- `DocumentMetadata`: Objeto com metadados estruturados
- Logs no console com estatísticas de extração

**Exemplo de Log:**
```json
{
  "url": "https://defesacivil.gov.br/manual-enchentes.pdf",
  "content_length": 2450,
  "deterministic_fields": 5,
  "llm_extraction_success": true,
  "confidence_score": 0.85,
  "disaster_categories_found": 2,
  "has_emergency_contacts": true,
  "has_instructions": true
}
```

### 2. Sub-trace: `deterministic_extraction`
**Função:** Extração baseada em regras determinísticas

**Detalhes:**
- Análise de padrões de URL (ex: defesacivil.gov.br → fonte oficial)
- Detecção de palavras-chave de categoria de desastre
- Identificação de elementos estruturais (telefones, listas numeradas)

### 3. Sub-trace: `llm_metadata_extraction`
**Função:** Classificação semântica via LLM com structured outputs

**Request para OpenAI:**
- Model: `gpt-4o-mini`
- Response Format: `LLMMetadataResponse` (Pydantic)
- Input: Conteúdo truncado (máx 4000 chars)

**Structured Output:**
```json
{
  "document_type": "manual",
  "information_type": "response",
  "target_audience": ["victim", "resident"],
  "area_type": "urban",
  "disaster_phase": "during"
}
```

### 4. Sub-trace: `metadata_validation`
**Função:** Validação de consistência dos metadados extraídos

**Validações:**
- Campos obrigatórios preenchidos
- Consistência semântica (ex: "response" + "before" = inválido)
- Score de confiança dentro do intervalo [0, 1]
- Categorias de desastre para urgência alta

## Traces de Pipeline de Documentos

### 5. Trace: `document_chunk_generation`
**Span Principal:** Geração de chunks enriquecidos com metadados

**Sub-processes:**
- Extração de metadados do documento
- Geração de chunks via DocumentChunker
- Enriquecimento de cada chunk com metadados específicos

### 6. Sub-trace: `chunk_metadata_extraction`
**Função:** Extração de metadados específicos por chunk

**Detecções por chunk:**
- Tipo de seção (introdução, procedimentos, contatos, mapas)
- Presença de contatos de emergência
- Instruções numeradas
- Densidade de informação

## Traces de Retrieval com Filtros

### 7. Trace: `document_retrieval_with_metadata`
**Span Principal:** Recuperação de documentos com filtros baseados em perfil

**Exemplo de Log:**
```json
{
  "user_profile": "victim",
  "filter_applied": true,
  "filter_conditions": 3
}
```

**Estatísticas de Retrieval:**
```json
{
  "total_candidates": 5,
  "relevant_docs_found": 2,
  "filter_effectiveness": 0.4
}
```

### 8. Sub-trace: `retrieval`
**Função:** Query no ChromaDB com filtros de metadados

**ChromaDB Query:**
```python
{
  "query_texts": "como evacuar em enchente",
  "n_results": 5,
  "where": {
    "$or": [
      {"information_type": "response"},
      {"urgency_level": {"$in": ["critical", "high"]}},
      {"target_audience": {"$in": ["victim"]}}
    ]
  }
}
```

### 9. Sub-trace: `retrieval_filtering`
**Função:** Filtro por similaridade e análise de metadados

**Exemplo de Log:**
```json
{
  "total_candidates": 5,
  "documents_with_metadata": 5,
  "documents_with_confidence": 4,
  "avg_confidence": 0.78,
  "metadata_fields_found": [
    "url", "document_type", "information_type", 
    "target_audience", "urgency_level", "confidence_score",
    "disaster_categories", "has_emergency_contacts"
  ],
  "docs_passed_similarity": 2
}
```

## Benefícios da Observabilidade

### Performance Monitoring
- Tempo de extração de metadados por documento
- Taxa de sucesso da classificação LLM
- Efetividade dos filtros de metadados

### Quality Assurance
- Scores de confiança dos metadados extraídos
- Validação de consistência semântica
- Cobertura de metadados nos documentos indexados

### User Experience
- Relevância dos documentos retornados por perfil
- Uso efetivo dos filtros automáticos
- Distribuição de tipos de consulta por perfil

### Debugging
- Traces completos do pipeline de extração
- Logs detalhados de cada etapa
- Visibilidade de falhas e fallbacks