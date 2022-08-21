# Fiação aérea na cidade de São Paulo

Processamento dos dados sobre fiação aérea utilizando levantamento LiDAR 3D na cidade de São Paulo.

## Motivação

São Paulo, assim como diversas outras cidades tem uma caraterística importante na paisagem urbana que interfere em muitos aspectos que vão além da estética e que merecem atenção na pesquisa, na gestão e na discussão sobre o espaço livre público. 

## Objetivo

Sendo assim, esse repositório se dedica a estudar, documentar e persistir métodos computacionais de inferir e mapear os locais e as nuances da fiação aérea na cidade de São Paulo.

## Materiais e Métodos

Atravéz de filtragens simples dos dados do ALS LiDAR 3D da cidade é possível destacar e validar visualmente os cabeamentos e fiações aéreas, seguindo os critérios considerando apenas os pontos que satisfassam as seguintes condições:
* Que seja o primeiro retorno `return_number == 1`
* Que a altura em relação ao solo seja maior que 4 metros `HAG >= 4`
* Que o valor da intensidade seja baixo, pŕoximo a 1 `intensity == 1`

Isso é possível fazer utilizando o software CloudCompare, conforme o vídeo

## Resultados

Os critérios estabelecidos destacar visualmente os cabeamentos aéreos e suas nuânces que podem ser convertidos em raster e quantficados em relação a densidade de pontos a cada unidade espacial, altura ou alturas (no caso de múltiplos níveis) em relação ao solo, continuidade, rede e ainda podem ser agregados espacialmente, por exemplo, em relação aos polígonos de calçada

## Próximos passos

* Estudar bibliografia e métodos sobre o tema
* Levantar a legislação para documentar e considerar a orientação dos resultados
* Estabelecer um critério ou método para validação dos resultados
* Discutir as limitações do método
* Desenvolver uma técnica para estudar a continuidade e criar uma rede de cabeamento a partir do raster de resultado
* Processar os dados para toda a cidade

## Considerações finais

Se estiver estudando o assunto, não deixe de entrar em contato e contribuir, pois o conhecimento evolui em passos curtos e de forma colaborativa. 
