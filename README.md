# Assistente RAG para Desastres Naturais

## Descrição

Assistente virtual inteligente que utiliza arquitetura RAG (Retrieval-Augmented Generation) para fornecer orientações personalizadas durante desastres naturais. O sistema indexa documentos oficiais de órgãos governamentais e adapta as respostas baseado no perfil do usuário (vítima, residente ou familiar), priorizando informações relevantes como procedimentos de emergência, contatos úteis e orientações de segurança em português.

## Versão em Produção

🔗 [https://disaster-rag-assistant.streamlit.app](https://disaster-rag-assistant.streamlit.app)

## Membros do Grupo

| Nome | RM |
|-----|-----|
| [Cristiano Washington Dias](https://github.com/criswd) | RM555992 |
| [Mizael Vieira Bezerra](https://github.com/mizaelvieira1) | RM555796 |
| [Santiago Bernardes](https://github.com/santiagonbernardes) | RM557447 |

## Como Rodar Localmente

### 1. Instale o UV

Siga as instruções de instalação na documentação oficial: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

### 2. Clone o repositório

```bash
git clone https://github.com/santiagonbernardes/disaster-rag-assistant.git
cd disaster-rag-assistant
```

### 3. Instale as dependências

```bash
uv sync
```

### 4. Configure as variáveis de ambiente

```bash
cp .streamlit/secrets.toml.SAMPLE .streamlit/secrets.toml
```

Edite o arquivo `.streamlit/secrets.toml` e adicione suas chaves de API:
- OpenAI API Key
- Langfuse Keys (Public e Secret)
- LlamaCloud API Key

> **⚠️ Importante**: Este projeto utiliza integração com Langfuse para gerenciamento de prompts e observabilidade. Os prompts são armazenados no Langfuse e não estão incluídos no repositório. Para utilizar o projeto, você precisará **solicitar as chaves de API específicas deste projeto** que incluem acesso aos prompts configurados.

### 5. Execute a aplicação

```bash
uv run streamlit run app.py
```

A aplicação estará disponível em http://localhost:8501

## Tecnologias Utilizadas

### Frontend e Interface
- **Streamlit**: Escolhido pela rapidez no desenvolvimento de interfaces interativas e facilidade de deployment, permitindo criar uma aplicação web completa em Python com componentes nativos para chat e navegação.

### Processamento de Linguagem Natural
- **Modelos OpenAI**: Utilização dinâmica de modelos LLM com suporte a structured outputs, garantindo consistência nas extrações de metadados e qualidade nas respostas contextualizadas.

### Retrieval e Busca Semântica
- **ChromaDB**: Banco vetorial escolhido pela simplicidade de setup, suporte nativo a metadados e capacidade de filtragem avançada, essencial para o sistema de perfis do usuário.
- **OpenAI Embeddings**: Embeddings text-embedding-3-small para representação semântica de documentos com boa relação custo-benefício.

### Processamento de Documentos
- **LlamaParse**: Serviço especializado em parsing de documentos PDF com alta precisão, mantendo estrutura e formatação original dos documentos oficiais.

### Observabilidade e Gerenciamento de Prompts
- **Langfuse**: Plataforma completa para observabilidade de aplicações LLM, permitindo versionamento de prompts, traces detalhados e monitoramento de performance em produção.

### Gerenciamento de Dependências
- **UV**: Gerenciador de dependências moderno e rápido para Python, oferecendo resolução de dependências mais eficiente que pip e melhor experiência de desenvolvimento.

## Estrutura do Projeto

```
├── app.py                         # Ponto de entrada da aplicação
├── src/
│   ├── ui/                        # Interface do usuário
│   │   ├── chatbot.py             # Interface principal do chat com RAG
│   │   └── settings.py            # Interface administrativa para indexação
│   ├── retrieval/                 # Sistema de recuperação de documentos
│   │   └── document.py            # Processamento e parsing de documentos
│   ├── services/                  # Serviços principais
│   │   ├── document_chunker.py    # Divisão de documentos em chunks
│   │   ├── metadata_extractor.py  # Extração de metadados estruturados
│   │   └── context_formatter.py   # Formatação XML para contexto do LLM
│   ├── repositories/              # Camada de dados
│   │   └── document_cache.py      # Sistema de cache de documentos
│   └── core/                      # Configurações centrais
│       └── logging_config.py      # Configuração de logs
├── tests/                         # Testes automatizados
│   ├── services/                  # Testes dos serviços
│   ├── ui/                        # Testes da interface
│   └── repositories/              # Testes dos repositórios
├── .streamlit/                    # Configurações do Streamlit
│   └── secrets.toml.SAMPLE        # Template de configuração
└── .cache/                        # Cache local de documentos
    └── documents/                 # Documentos processados e chunks
```