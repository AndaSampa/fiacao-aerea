import pdal
import json
import geopandas as gpd
from shapely.geometry import Polygon
import pandas as pd
from sqlalchemy import create_engine, text
import glob
import sys
import os
import shutil
from multiprocessing import Pool

gdf_articulacao = gpd.read_file("zip://downloads/SIRGAS_SHP_quadriculamdt.zip!/SIRGAS_SHP_quadriculamdt/")
engine = create_engine("postgresql://postgres:1234@localhost:5433/gis")

class Scm:
    def __init__(self, scm) -> None:
        
        self.geometry = gdf_articulacao.set_index('qmdt_cod').loc[scm].geometry
        self.scm = scm

def pipeline_fiacao(scm):
    pipeline = [
        {
            "type": "readers.las",
            "filename": f'data/sample/MDS_color_{scm}.laz',
            "override_srs": "EPSG:31983"
        },
        {
            "type":"filters.range",
            "limits":"ReturnNumber[1:4],NumberOfReturns![1:1],UserData[3:],Intensity[:10],Classification[19:19]"
        },
        {
            "type":"filters.voxelcentroidnearestneighbor",
            "cell":0.50
        },
        {
            "type":"filters.outlier",
            "method":"radius",
            "radius":2.0,
            "min_k":4
        },
        {
            "type":"filters.range",
            "limits":"Classification![7:7]"
        },
        {
            "type":"writers.las",
            "filename": f'results/sample/MDS_{scm}_1000-filtered.laz'
        },
        {
            "type":"writers.text",
            "format":"csv",
            "order":"X,Y",
            "keep_unspecified":"false",
            "filename":f"results/sample/MDS_{scm}_1000-filtered.csv"
        }
        
    ]
    return pipeline

def pipeline_massa_arborea(smc):
    pipeline = [
        {
            "type": "readers.las",
            "filename": f'data/sample/MDS_color_{smc}.laz',
            "override_srs": "EPSG:31983"
        },
        {
            "type":"filters.range",
            "limits":"ReturnNumber[1:4],NumberOfReturns![1:1],UserData[3:],Classification[5:5]"
        },
        {
            "type": "filters.assign",
            "value" : "Z = 1"
        },
        {
            "filename":f"results/sample/MDS_{smc}-vegetation.tiff",
            "gdaldriver":"GTiff",
            "output_type":"max",
            "resolution":"1",
            "type": "writers.gdal",
            "gdalopts":"COMPRESS=ZSTD, PREDICTOR=3, BIGTIFF=YES",
            # "width": scm_att.width,
            # "height": scm_att.height,
            # "origin_x": scm_att.origin_x,
            # "origin_y": scm_att.origin_y,
            "nodata":"0",
            "data_type": "float32",
            "where": "(Classification == 5)",
            "default_srs": "EPSG:31983"
        },
    ] 
    return pipeline  

def processa(scm):
    # Processando o pipeline da fiacao
    fiacao = pdal.Pipeline(json.dumps(pipeline_fiacao(scm)))
    _ = fiacao.execute()

    # Lendo pontos
    df_xy = pd.read_csv(f'results/sample/MDS_{scm}_1000-filtered.csv')
    gdf_xy = gpd.GeoDataFrame(geometry=gpd.points_from_xy(x = df_xy.X, y = df_xy.Y))

    # Gerando buffer
    gdf_xy.geometry = gdf_xy.buffer(2.5)
    gdf_xy = gdf_xy.dissolve()
    # gdf_xy = gdf_xy.simplify(1).explode().reset_index()
    # gdf_xy.geometry = gdf_xy.geometry.make_valid()

    # Abrindo no PostGis
    gdf_xy = gpd.GeoDataFrame(geometry=gdf_xy.simplify(1))
    gdf_xy = gdf_xy.explode()
    gdf_xy.geometry = gdf_xy.geometry.exterior
    gdf_xy.geometry = gdf_xy.geometry.apply(lambda x: Polygon(x.coords))
    # gdf_xy.geometry = gdf_xy.geometry.make_valid()
    gdf_xy.loc[gdf_xy.is_valid].reset_index().to_postgis('fiacao_buffer_dissolvido', engine, if_exists='replace')
    # gerando a query
    query = f'select ST_ApproximateMedialAxis(geometry) as geometry from "fiacao_buffer_dissolvido";'

    # gerando resultados
    gdf_fiacao = gpd.read_postgis(text(query), con=engine.connect(), geom_col='geometry')
    gdf_fiacao = gdf_fiacao.set_crs(epsg=31983, allow_override=True)
    gdf_fiacao = gdf_fiacao.loc[(gdf_fiacao.length > 10.0), :]
    
    # recortar pela geometria do SCM
    gdf_fiacao = gdf_fiacao.clip(Scm(scm).geometry)
    # simplificar a geometria resultante
    gdf_fiacao.geometry = gdf_fiacao.geometry.simplify(1)
    # Salva o resultado
    gdf_fiacao.to_file(f'results/sample/fiacao_{scm}.gpkg', driver='GPKG')

    # remover tabela do PostGis
    # drop = f'DROP TABLE IF EXISTS "fiacao_buffer_dissolvido_{scm}";'
    # print('passando ...')
    # with engine.connect() as connection:
    #     _ = connection.execute(text(drop))
    #     connection.commit()

    # print("passou!")

    ## Massa Arbórea e conflitos

    # processa pipeline massa arbórea
    massa_arborea = pdal.Pipeline(json.dumps(pipeline_massa_arborea(scm)))
    _ = massa_arborea.execute()

    # gera polígono dos contornos da massa arbórea
    os.system(f'gdal_contour -p -amax ELEV_MAX -amin ELEV_MIN -b 1 -i 1.0 -f "GPKG" /home/feromes/dev/fiacao-aerea/results/sample/MDS_{scm}-vegetation.tiff /home/feromes/dev/fiacao-aerea/results/sample/MDS_{scm}-vegetacao-countor.gpkg')

    gdf_countor = gpd.read_file(f'results/sample/MDS_{scm}-vegetacao-countor.gpkg')
    gdf_countor = gpd.GeoDataFrame(gdf_countor.explode().reset_index())

    # gdf_fiacao = gpd.read_file(f'results/sample/fiacao_{scm}.gpkg', driver='GPKG')
    gdf_countor.set_crs(epsg=31983, inplace=True)

    # adicionando um buffer de 1m nos contornos da massa arborea
    gdf_countor.geometry = gdf_countor.buffer(1)

    # verificando interseccao (prováveis conflitos)
    gdf_countor_intersects = gdf_countor.sjoin(gdf_fiacao)

    # retornando o buffer
    gdf_countor_intersects.geometry = gdf_countor_intersects.buffer(-1)

    ## TODO 
    # salvar a quantidade de conflitos prováveis

    # recortar pela geometria do SCM
    gdf_countor_intersects = gdf_countor_intersects.clip(Scm(scm).geometry)

    # salvando o resultado dos conflitos
    gdf_countor_intersects.to_file(f'results/sample/arvores_com_interseccao_com_rede_{scm}.gpkg', driver='GPKG')

    return None

def processa_tudo():
    folder = ('data/sample/*.laz')
    for file in glob.glob(folder):
        scm = file.split('.')[0][-8:]
        print(scm)
        processa(scm)
    return None

def pos_processamento():
    ## TODO
    # Executar o pos processamento unindo e contabilizando os arquivos
    # gerar output da porcentagem de processamento
    return None

def main():
    print('Processamento fiação elétrica de Dados LIDAR Sampa 2017 ***')
    if len(sys.argv) > 1:
        # Processa os SCMS na sequencia
        for scm in sys.argv[1:]:
            print(Scm(scm).scm)
            processa(scm)
    else:
        # print(Scm(scm).scm)
        processa_tudo()

if __name__ == '__main__':
    main()