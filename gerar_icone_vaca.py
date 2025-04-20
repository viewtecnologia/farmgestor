#!/usr/bin/env python3
"""
Gerador de ícone SVG para o mapa RuralSys
Este script gera um ícone de vaca SVG para uso no mapa do sistema.
"""
import os

def gerar_icone_vaca(cor_cabeca="#FF6666", cor_corpo="#FFFFFF", cor_manchas="#000000", tamanho=64):
    """
    Gera um SVG de ícone de vaca estilizado para o mapa
    
    Args:
        cor_cabeca: Cor da cabeça da vaca (hex)
        cor_corpo: Cor do corpo da vaca (hex)
        cor_manchas: Cor das manchas (hex)
        tamanho: Tamanho do ícone em pixels
    
    Returns:
        Conteúdo do SVG como string
    """
    # Calcular o scaling apropriado com base no tamanho desejado
    scale_factor = tamanho / 64
    
    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{tamanho}px" height="{tamanho}px" viewBox="0 0 64 64" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <title>Ícone Vaca</title>
    <g id="icone-vaca" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
        <!-- Contorno -->
        <path d="M60,32 C60,47.464 47.464,60 32,60 C16.536,60 4,47.464 4,32 C4,16.536 16.536,4 32,4 C47.464,4 60,16.536 60,32 Z" id="circulo-fundo" fill="#F8F8F8" fill-opacity="0.8"></path>
        
        <!-- Corpo da vaca -->
        <path d="M46,30 C46,34 44,40 34,40 C24,40 18,36 18,30 C18,24 22,20 32,20 C42,20 46,26 46,30 Z" id="corpo" fill="{cor_corpo}" stroke="{cor_manchas}" stroke-width="2"></path>
        
        <!-- Cabeça da vaca -->
        <path d="M18,30 C18,30 14,30 12,32 C10,34 10,36 12,38 C14,40 18,38 18,36 L18,30 Z" id="cabeca" fill="{cor_cabeca}" stroke="{cor_manchas}" stroke-width="2"></path>
        
        <!-- Olho -->
        <circle id="olho" fill="{cor_manchas}" cx="13" cy="35" r="1"></circle>
        
        <!-- Chifres -->
        <path d="M14,31 C14,31 13,29 11,29 M14,31 C14,31 13,28 15,28" id="chifres" stroke="{cor_manchas}" stroke-width="1.5"></path>
        
        <!-- Pernas -->
        <path d="M24,40 L22,46 M36,40 L38,46 M28,40 L28,46 M32,40 L32,46" id="pernas" stroke="{cor_manchas}" stroke-width="2" stroke-linecap="round"></path>
        
        <!-- Manchas -->
        <path d="M38,25 C38,25 42,28 38,32 C34,36 28,30 38,25 Z" id="mancha1" fill="{cor_manchas}"></path>
        <path d="M28,30 C28,30 30,34 26,34 C22,34 24,28 28,30 Z" id="mancha2" fill="{cor_manchas}"></path>
        
        <!-- Rabo -->
        <path d="M46,30 C46,30 50,28 52,32 C52,36 48,38 48,38" id="rabo" stroke="{cor_manchas}" stroke-width="1.5" fill="none"></path>
        <path d="M52,32 C52,32 54,30 54,34" id="ponta-rabo" stroke="{cor_manchas}" stroke-width="1.5" fill="{cor_cabeca}"></path>
    </g>
</svg>'''
    
    return svg

def salvar_svg(conteudo, caminho):
    """Salva o conteúdo SVG em um arquivo"""
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print(f"SVG salvo em: {caminho}")

def main():
    """Função principal"""
    # Gerar ícone padrão
    svg_padrao = gerar_icone_vaca()
    salvar_svg(svg_padrao, 'static/img/icone_vaca_padrao.svg')
    
    # Gerar algumas variações 
    cores_cabeca = ["#FF6666", "#FF9966", "#FFD166", "#119DA4", "#6A0572"]
    nomes_cores = ["vermelho", "laranja", "amarelo", "azul", "roxo"]
    
    os.makedirs('static/img/icones', exist_ok=True)
    
    for i, (cor, nome) in enumerate(zip(cores_cabeca, nomes_cores)):
        svg = gerar_icone_vaca(cor_cabeca=cor)
        salvar_svg(svg, f'static/img/icones/vaca_{nome}.svg')
        
        # Criar uma versão com mancha diferente
        svg_alt = gerar_icone_vaca(cor_cabeca=cor, cor_manchas="#3D3D3D" if i % 2 == 0 else "#774936")
        salvar_svg(svg_alt, f'static/img/icones/vaca_{nome}_alt.svg')
    
    print("Geração de ícones concluída com sucesso!")

if __name__ == "__main__":
    main()