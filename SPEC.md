# Conversor HEIC para JPG by Jair Lima

## Objetivo

Criar um utilitario executavel periodicamente para varrer `C:\Users\jairs\Pictures` e subpastas, localizar arquivos `.heic` e converter apenas os que ainda nao possuem `.jpg` equivalente.

## Escopo

O aplicativo deve:

1. Percorrer recursivamente uma pasta raiz.
2. Identificar arquivos HEIC sem JPG equivalente.
3. Converter HEIC para JPG usando `ffmpeg`.
4. Preservar as datas do arquivo original no JPG gerado.
5. Exibir um resumo de convertidos, ignorados e falhas.
6. Salvar o progresso para continuar automaticamente em nova execucao.
7. Permitir reinicio explicito da varredura completa.
8. Exibir progresso e pasta atual de forma clara no console.

## Fora de escopo

1. Interface grafica.
2. Publicacao automatica no GitHub.
3. Remocao do arquivo HEIC original.

## Arquitetura

1. `convert_heic_to_jpg.py`, script principal em Python.
2. `run_converter.bat`, atalho para execucao manual ou agendada no Windows.
3. `build_exe.bat`, empacotamento em executavel Windows.
4. `README.md`, instrucoes de uso.

## Dependencias

1. Python 3.
2. `ffmpeg` disponivel no `PATH`.

## Decisoes

1. Conversao feita via `ffmpeg`, porque o ambiente atual ja possui suporte a HEIC.
2. Preservacao de timestamps feita em nivel de sistema de arquivos, copiando criacao, modificacao e ultimo acesso do HEIC para o JPG.
3. O script nao sobrescreve JPG existente por padrao.
4. O progresso e salvo em `heic_converter_state.json` ao longo da execucao.
5. O executavel alvo para distribuicao local e `ConversorHeicJpgJair.exe`.
6. A saida do console deve dar retorno imediato para reduzir a percepcao de travamento.

## Pendencias

1. Se no futuro for necessario preservar campos EXIF adicionais de forma garantida, avaliar integracao com `exiftool`.

## Criterios de aceite

1. O script encontra `.heic` em subpastas.
2. Um `.jpg` novo e gerado quando nao existe equivalente.
3. Um `.jpg` existente nao e recriado por padrao.
4. As datas do arquivo gerado ficam iguais as do HEIC original.
5. A execucao retorna resumo legivel.
6. Uma interrupcao por teclado permite continuar na proxima execucao.
7. O parametro `--restart` faz a varredura completa desde o inicio.
8. O operador consegue ver a pasta atual em processamento durante a execucao.

## Instrucoes operacionais

1. Execucao manual:
   `python convert_heic_to_jpg.py`
2. Execucao com simulacao:
   `python convert_heic_to_jpg.py --dry-run`
3. Reinicio completo:
   `python convert_heic_to_jpg.py --restart`
4. Empacotamento do executavel:
   `build_exe.bat`
5. Execucao por lote:
   `run_converter.bat`
