# Dados de entrada

Coloque nesta pasta o arquivo `blocos.tgz` fornecido na atividade.
O arquivo tem aproximadamente 207 MB e não está versionado neste repositório.

SHA-256 do arquivo utilizado:

```text
679fe208f9a807fdd38e9d64948c73581af3e99ca52fb707ce06937e67bc536d
```

O comando `python -m src.extract_data` lê os 98 blocos JSON diretamente do arquivo
compactado e cria `transactions.csv.gz` nesta pasta. O treinamento cria também
`partitions.csv.gz`, com a divisão de cada transação entre desenvolvimento e teste.
Essas tabelas são derivadas dos blocos e também ficam fora do Git.
