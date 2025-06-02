#!/usr/bin/env python3
"""Example demonstrating DocumentChunker usage."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.document_chunker import DocumentChunker


def main():
    # Sample emergency guide text
    sample_text = """
    GUIA DE EMERGÊNCIA PARA ENCHENTES

    Introdução: Este guia fornece informações essenciais para situações de enchente. 
    É importante manter a calma e seguir as orientações das autoridades locais.

    Antes da Enchente:
    Prepare um kit de emergência com água, alimentos não perecíveis, medicamentos, 
    documentos importantes e lanternas. Identifique rotas de evacuação e abrigos próximos. 
    Mantenha-se informado através de rádio ou televisão sobre alertas meteorológicos.

    Durante a Enchente:
    Nunca tente atravessar águas em movimento. Seis polegadas de água em movimento 
    podem derrubar você. Um pé de água pode fazer seu veículo flutuar. Se precisar 
    evacuar, desligue o gás e a eletricidade. Vá para terrenos mais altos imediatamente.

    Após a Enchente:
    Retorne para casa apenas quando as autoridades declararem que é seguro. Evite 
    água parada, pois pode estar contaminada ou eletrificada. Documente danos para 
    o seguro com fotos. Descarte alimentos que tiveram contato com a água da enchente.

    Contatos de Emergência:
    Defesa Civil: 199
    Bombeiros: 193
    SAMU: 192
    Polícia: 190
    """

    # Create chunker with small size for demonstration
    chunker = DocumentChunker(chunk_size=300, overlap=50)

    # Chunk the document
    chunks = chunker.chunk_document(
        sample_text, metadata={"source": "emergency_guide.pdf", "type": "flood_guide"}
    )

    # Display results
    print(f"Document split into {len(chunks)} chunks\n")
    print("-" * 80)

    for chunk in chunks:
        print(f"Chunk {chunk.index + 1}/{chunk.metadata['total_chunks']}:")
        print(f"Size: {len(chunk.content)} characters")
        print(f"Position: {chunk.start_char}-{chunk.end_char}")
        print(f"Content preview: {chunk.content[:100]}...")
        print("-" * 80)

    # Show overlap example
    if len(chunks) > 1:
        print("\nOverlap demonstration:")
        print(f"End of chunk 1: ...{chunks[0].content[-50:]}")
        print(f"Start of chunk 2: {chunks[1].content[:50]}...")


if __name__ == "__main__":
    main()