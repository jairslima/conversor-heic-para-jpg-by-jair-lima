# Conversor HEIC para JPG by Jair Lima

Utilitario para varrer `C:\Users\jairs\Pictures` e converter arquivos `.heic` para `.jpg` apenas quando o JPG equivalente ainda nao existir.

## Requisitos

1. Windows com Python 3.
2. `ffmpeg` instalado e disponivel no `PATH`.

## Como usar

Execucao padrao:

```powershell
python .\convert_heic_to_jpg.py
```

O programa tenta continuar automaticamente de onde parou, se existir um estado salvo no arquivo `heic_converter_state.json`.

Simulacao sem gravar arquivos:

```powershell
python .\convert_heic_to_jpg.py --dry-run
```

Recomecando do inicio e ignorando o estado salvo:

```powershell
python .\convert_heic_to_jpg.py --restart
```

Executando sem retomar o estado salvo apenas nesta chamada:

```powershell
python .\convert_heic_to_jpg.py --no-resume
```

Definindo outra pasta raiz:

```powershell
python .\convert_heic_to_jpg.py --root "D:\Minhas Fotos"
```

Forcando reconversao mesmo se o JPG existir:

```powershell
python .\convert_heic_to_jpg.py --force
```

## Pausa, saida e continuidade

1. Durante a execucao, `Ctrl+C` pausa e salva o progresso.
2. Na proxima execucao, o programa continua automaticamente do proximo arquivo pendente.
3. Para comecar tudo de novo, use `--restart`.
4. Para manter a janela aberta ao final, use `--pause-on-finish`.

## Executavel

Gerando o `.exe`:

```powershell
.\build_exe.bat
```

Executavel gerado:

```text
C:\Users\jairs\Codex\Conversor HEIC para JPG by Jair Lima\dist\ConversorHeicJpgJair\ConversorHeicJpgJair.exe
```

## Execucao periodica

O arquivo `run_converter.bat` facilita a chamada no Agendador de Tarefas do Windows.

Programa:

```text
C:\Users\jairs\Codex\Conversor HEIC para JPG by Jair Lima\run_converter.bat
```

## Proximo passo sugerido

Criar uma tarefa no Agendador de Tarefas do Windows para executar o conversor em horario recorrente, por exemplo uma vez por dia ou uma vez por semana.

## Comportamento

1. Procura `.heic` de forma recursiva.
2. Considera equivalente o arquivo com o mesmo nome base e extensao `.jpg` ou `.jpeg`.
3. Usa `ffmpeg` para gerar o JPG.
4. Replica criacao, ultima modificacao e ultimo acesso do HEIC no JPG final.
5. Salva estado para continuar depois, quando a execucao for interrompida.
6. Mantem visivel a pasta atual no log e no titulo da janela.
7. Mostra um resumo ao terminar.

## Observacao

O script nao apaga o arquivo `.heic` original.
