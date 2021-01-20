import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from difflib import SequenceMatcher
from sklearn.linear_model import Ridge
import pickle
import time
import seaborn as sns
import locale
from fake_useragent import UserAgent
import re
import matplotlib.pyplot as plt
import matplotlib
from flask import Flask, render_template, request, redirect
import io
import base64

locale.setlocale(locale.LC_ALL, 'en_US')
application = Flask(__name__, template_folder='templates')

#Common file for translation
Translation=pd.read_csv('Translation_file.csv',encoding='cp932')

#Definition Region 
NORTH=['Hokkaido','Aomori Prefecture','Akita Prefecture','Iwate Prefecture','Yamagata Prefecture','Miyagi Prefecture','Fukushima Prefecture']
KANTO_1=['Tokyo','Kanagawa Prefecture']
KANTO_2=['Saitama Prefecture','Chiba Prefecture','Ibaraki Prefecture','Tochigi Prefecture','Gunma Prefecture']
CENTRAL=['Niigata Prefecture','Toyama Prefecture','Ishikawa Prefecture','Fukui Prefecture',
         'Gifu Prefecture','Aichi Prefecture','Shizuoka Prefecture','Yamanashi Prefecture',
         'Nagano Prefecture']
KANSAI_1=['Mie Prefecture','Nara Prefecture','Wakayama Prefecture','Osaka Prefecture']
KANSAI_2=['Shiga Prefecture','Kyoto Prefecture','Hyogo Prefecture']
WEST=['Tottori Prefecture','Shimane Prefecture', 'Okayama Prefecture','Hiroshima Prefecture','Yamaguchi Prefecture']
SHIKOKU=['Kagawa Prefecture','Tokushima Prefecture','Ehime Prefecture','Kochi Prefecture']
KYUSHU=['Fukuoka Prefecture','Saga Prefecture','Nagasaki Prefecture','Kumamoto Prefecture','Oita Prefecture',
        'Miyazaki Prefecture','Kagoshima Prefecture','Okinawa Prefecture']

#Model result input
House_model_result=pd.read_csv('House_Final_Summary.csv')
Mansion_model_result=pd.read_csv('Mansion_Final_Summary.csv')

#Function to convert graph to base 64 format
def fig_to_base64(fig):
    img = io.BytesIO()
    fig.figure.savefig(img, format='png',
                bbox_inches='tight')
    img.seek(0)
    return base64.b64encode(img.getvalue())


def Sumo_get_html_info(link):
    ua = UserAgent()
    headers ={'User-Agent':str(ua.chrome)}
    try:
        request=requests.get(link,headers=headers,timeout=1)
    except:
        try:
            time.sleep(1)
            request=requests.get(link,headers=headers,timeout=1)
        except:
            time.sleep(3)
            request=requests.get(link,headers=headers,timeout=1)
    content=request.content
    soup=BeautifulSoup(content,'html.parser')
    Info_elem=soup.find('h3',{'class':'secTitleInnerR'})
    if Info_elem==None:
        Info_elem=soup.find('h3',{'class':'secTitleInnerK'})
    if '一戸建て' in Info_elem.text.strip():
        Type='House'
    else:
        Type='Mansion'
    return soup,Type

def Sumo_get_region_city_planning(HTML_info):
    try:
        for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
            if '商業' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or '１種' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or  '２種' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or '工業' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
                Pos=i
        City_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
        City_elem=City_elem.text.strip()

        if '１種低' in City_elem:
            I_low_residential=1
        else:
            I_low_residential=0
        if '１種住' in City_elem:
            I_residential=1
        else:
            I_residential=0
        if '１種中' in City_elem:
            I_high_residential=1
        else:
            I_high_residential=0
        if '２種中' in City_elem:
            II_high_residential=1
        else:
            II_high_residential=0
        if '調整' in City_elem:
            Control=1
        else:
            Control=0
        if '非線' in City_elem:
            Non_div=1
        else:
            Non_div=0
        if '準工業' in City_elem and '専用' not in City_elem:
            Quasi_ind=1
        else:
            Quasi_ind=0
        if '２種住' in City_elem:
            II_residential=1
        else:
            II_residential=0
        if '隣商業' in City_elem:
            Quasi_comm=1
        else:
            Quasi_comm=0
        if '商業' in City_elem and '隣' not in City_elem:
            comm=1
        else:
            comm=0
        if '工業' in City_elem and '準' not in City_elem and '専用' not in City_elem:
            Ind=1
        else:
            Ind=0
        if '二種低' in City_elem:
            II_low_residential=1
        else:
            II_low_residential=0
        if '準住宅' in City_elem:
            Quasi_resid=1
        else:
            Quasi_resid=0
        if '準都' in City_elem:
            Quasi_plan=1
        else:
            Quasi_plan=0
        if '都' in City_elem and '外' in City_elem:
            Out_plan=1
        else:
            Out_plan=0
        if '工業専用' in City_elem:
            exc_ind=1
        else:
            exc_ind=0

        #Get region-type
        if exc_ind==1 or Ind==1 or Quasi_ind==1:
            Industrial_area=1
        else:
            Industrial_area=0
        if Quasi_comm==1 or comm==1:
            Commercial_area=1
        else:
            Commercial_area=0
        if exc_ind==0 and Ind==0 and Quasi_ind==0 and Quasi_comm==0 and comm==0:
            Residential_area=1
        else:
            Residential_area=0
    except:
        I_low_residential=0
        I_residential=0
        I_high_residential=0
        II_high_residential=0
        Control=0
        Non_div=0
        Quasi_ind=0
        II_residential=0
        Quasi_comm=0
        comm=0
        Ind=0
        II_low_residential=0
        Quasi_resid=0
        Quasi_plan=0
        Out_plan=0
        exc_ind=0
        Industrial_area=0
        Commercial_area=0
        Residential_area=0

        
    return I_low_residential,I_residential,I_high_residential,II_high_residential,Control,Non_div,Quasi_ind,II_residential,Quasi_comm,comm,Ind,II_low_residential,Quasi_resid,Quasi_plan,Out_plan,exc_ind,Industrial_area,Commercial_area,Residential_area
    
def Sumo_get_prefecture(HTML_info):
    Pref_elem=HTML_info.find('p',{'class':'mt5 b'})
    Pref=Pref_elem.text.strip()[:3]
    S=[]
    Pref_translation=pd.read_csv('Translation_file.csv',encoding = 'cp932')
    Pref_translation=Pref_translation[['Prefecture_Jp','Prefecture_Eng']]
    Pref_translation=Pref_translation.drop_duplicates(subset=['Prefecture_Jp','Prefecture_Eng']).reset_index(drop=True)
    for i in range(len(Pref_translation)):
        if Pref in Pref_translation['Prefecture_Jp'][i]:
            S.append(1)
        else:
            S.append(0)
    Pref_translation['Check']=S
    if Pref_translation['Check'].sum()==1:
        Pref_translation=Pref_translation[Pref_translation['Check']==1].reset_index(drop=True)
        Final_pref=Pref_translation['Prefecture_Eng'][0]
    else:
        if Pref_translation['Check'].sum()>1:
            Pref_translation=Pref_translation[Pref_translation['Check']==1].reset_index(drop=True)
        else:
            pass
        Phonetic_check=pd.DataFrame()
        Phonetic_check['Pref']=Pref_translation['Prefecture_Jp']
        Score=[]
        for i in range(len(Phonetic_check)):
            Score.append(SequenceMatcher(None,Pref,Phonetic_check['Pref'][i]).ratio())
        Phonetic_check['Score']=Score
        Phonetic_check=Phonetic_check.sort_values(by=['Score'], ascending=[False])
        Phonetic_check=Phonetic_check.reset_index(drop=True)
        Pref=Phonetic_check['Pref'][0]
        S=[]
        for i in range(len(Pref_translation)):
            if Pref in Pref_translation['Prefecture_Jp'][i]:
                S.append(1)
            else:
                S.append(0)
        Pref_translation['Check']=S
        if len(S)>0:
            Pref_translation=Pref_translation[Pref_translation['Check']==1].reset_index(drop=True)
            Final_pref=Pref_translation['Prefecture_Eng'][0]
        else:
            Final_pref=-1
   
    return Final_pref


def Sumo_get_municipality(HTML_info):
    Mun_elem=HTML_info.find('p',{'class':'mt5 b'})
    Mun=0
    for i in ['県','府','都','道']:
        for k in ['区','市','村','町']:
            if i in Mun_elem.text.strip() and k in Mun_elem.text.strip():
                Mun_=Mun_elem.text.strip()
                Pos_1=Mun_.find(i)
                Pos_2=Mun_.find(k)
                Mun=Mun_[Pos_1+1:Pos_2+1]
                break
    if Mun==0:
        Mun=Mun_elem.text.strip()[3:]
    S=[]
    Mun_translation=pd.read_csv('Translation_file.csv',encoding = 'cp932')
    Mun_translation=Mun_translation[['Municipality_Jp','Municipality_Eng']]
    Mun_translation=Mun_translation.drop_duplicates(subset=['Municipality_Jp','Municipality_Eng']).reset_index(drop=True)
    for i in range(len(Mun_translation)):
        if Mun in Mun_translation['Municipality_Jp'][i]:
            S.append(1)
        else:
            S.append(0)
    Mun_translation['Check']=S
    if Mun_translation['Check'].sum()==1:
        Mun_translation=Mun_translation[Mun_translation['Check']==1].reset_index(drop=True)
        Mun=Mun_translation['Municipality_Jp'][0]
        Final_mun=Mun_translation['Municipality_Eng'][0]
    else:
        if Mun_translation['Check'].sum()>1:
            Mun_translation=Mun_translation[Mun_translation['Check']==1].reset_index(drop=True)
        else:
            pass
        Phonetic_check=pd.DataFrame()
        Phonetic_check['Mun']=Mun_translation['Municipality_Jp']
        Score=[]
        for i in range(len(Phonetic_check)):
            Score.append(SequenceMatcher(None,Mun,Phonetic_check['Mun'][i]).ratio())
        Phonetic_check['Score']=Score
        Phonetic_check=Phonetic_check.sort_values(by=['Score'], ascending=[False])
        Phonetic_check=Phonetic_check.reset_index(drop=True)
        Mun_=Phonetic_check['Mun'][0]
        S=[]
        for i in range(len(Mun_translation)):
            if Mun_ in Mun_translation['Municipality_Jp'][i]:
                S.append(1)
            else:
                S.append(0)
        Mun_translation['Check']=S
        if len(S)>0:
            Mun_translation=Mun_translation[Mun_translation['Check']==1].reset_index(drop=True)
            Final_mun=Mun_translation['Municipality_Eng'][0]
        else:
            Final_mun=-1


    return Mun,Final_mun

def Sumo_get_district(HTML_info,Mun,Final_mun):
    if Final_mun!=-1:
        for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
            if Mun in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
                Pos=i
        Dist_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
        Dist=Dist_elem.text.strip() 
        Dist_pos=None

        if '郡' in Dist:
            if len(Dist[Dist.find('郡')+1:])<2 or (len(Dist[Dist.find('郡')+1:])==2 and Dist[Dist.find('郡')+1:][-1] in ['0','1','2','3','4','5','6','7','8','9','０','１','２','３','４','５','６','７','８','９']):
                pass
        else:
            Dist_pos=Dist.find('郡')
        if Dist_pos==None:
            if '区'in Dist:
                Dist_pos=Dist.find('区')
            elif '市'in Dist:
                Dist_pos=Dist.find('市')
            else:
                Dist_pos=5
        Dist=Dist[Dist_pos+1:]
        Dist=Dist.replace('０','0')
        Dist=Dist.replace('１', '1')
        Dist=Dist.replace('２','2')
        Dist=Dist.replace('３','3')
        Dist=Dist.replace('４','4')
        Dist=Dist.replace('５','5')
        Dist=Dist.replace('６','6')
        Dist=Dist.replace('７','7')
        Dist=Dist.replace('８','8')
        Dist=Dist.replace('９','9')
        Dist_ref=pd.read_csv('Translation_file.csv',encoding = 'cp932')
        Dist_ref=Dist_ref[Dist_ref['Municipality_Eng']==Final_mun].reset_index(drop=True)
        Dist_ref=Dist_ref.drop_duplicates(subset=['District_Jp','District_Eng']).reset_index(drop=True)

        S=[]
        for i in range(len(Dist_ref)):
            if Dist in Dist_ref['District_Jp'][i]:
                S.append(1)
            else:
                S.append(0)
        Dist_ref['Check']=S
        if Dist_ref['Check'].sum()==1:
            Dist_ref=Dist_ref[Dist_ref['Check']==1].reset_index(drop=True)
            Final_dist=Dist_ref['District_Eng'][0]
        else:
            if Dist_ref['Check'].sum()>1:
                Dist_ref=Dist_ref[Dist_ref['Check']==1].reset_index(drop=True)
            else:
                pass
            Phonetic_check=pd.DataFrame()
            Phonetic_check['Dist']=Dist_ref['District_Jp']
            Score=[]
            for i in range(len(Phonetic_check)):
                Score.append(SequenceMatcher(None,Dist,Phonetic_check['Dist'][i]).ratio())
            Phonetic_check['Score']=Score
            Phonetic_check=Phonetic_check.sort_values(by=['Score'], ascending=[False])
            Phonetic_check=Phonetic_check.reset_index(drop=True)
            Dist=Phonetic_check['Dist'][0]
            S=[]
            for i in range(len(Dist_ref)):
                if Dist in Dist_ref['District_Jp'][i]:
                    S.append(1)
                else:
                    S.append(0)
            Dist_ref['Check']=S
            if len(S)>0:
                Dist_ref=Dist_ref[Dist_ref['Check']==1].reset_index(drop=True)
                Final_dist=Dist_ref['District_Eng'][0]
            else:
                Final_dist=-1
    else:
        Final_dist=-1
    return Final_dist


def Sumo_get_station(HTML_info,Municipality):
    if Municipality!=-1:
        for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
            if '歩' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
                Pos=i
        Sta_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
        Sta=Sta_elem.text.strip()   
        LIST=[i for i, letter in enumerate(Sta) if letter == '歩']

        if 'ＪＲ' in Sta or '線' in Sta or '地下鉄' in Sta or 'メトロ' or 'ライン' in Sta:
            for i in range(len(LIST)):
                if i==0:
                    Pos_=LIST[0]
                    Sta_=Sta[:Pos_]
                    if 'ＪＲ' in Sta_ or '線' in Sta_ or '地下鉄' in Sta_ or 'メトロ' in Sta_ or 'ライン' in Sta_:
                        Sta_pos=Sta_.find('「')
                        Sta_pos2=Sta_.find('」')
                        Sta_=Sta_[Sta_pos+1:Sta_pos2]
                        Sta_=Sta_.replace('０','0')
                        Sta_=Sta_.replace('１', '1')
                        Sta_=Sta_.replace('２','2')
                        Sta_=Sta_.replace('３','3')
                        Sta_=Sta_.replace('４','4')
                        Sta_=Sta_.replace('５','5')
                        Sta_=Sta_.replace('６','6')
                        Sta_=Sta_.replace('７','7')
                        Sta_=Sta_.replace('８','8')
                        Sta_=Sta_.replace('９','9')
                        Sta_translation=pd.read_csv('Translation_file.csv',encoding = 'cp932')
                        Sta_translation=Sta_translation[Sta_translation['Municipality_Eng']==Municipality].reset_index(drop=True)
                        Sta_translation=Sta_translation.drop_duplicates(subset='Station_Jp').reset_index(drop=True)
                        Sta_translation=Sta_translation.dropna().reset_index(drop=True)
                        if len(Sta_translation)==1:
                            Final_sta=Sta_translation['Station_Eng'][0]
                            break
                        else:
                            for k in range(len(Sta_translation['Station_Jp'])):
                                if Sta_ in Sta_translation['Station_Jp'][k] and '(' in Sta_translation['Station_Jp'][k] and ')' in Sta_translation['Station_Jp'][k]:
                                    if Sta_[-1]==Sta_translation['Station_Jp'][k][Sta_translation['Station_Jp'][k].find('(')-1]:
                                        Sta_translation=Sta_translation[Sta_translation['Station_Jp']==Sta_translation['Station_Jp'][k]].reset_index(drop=True)
                                        Final_sta=Sta_translation['Station_Eng'][0]
                                        break
                            if len(Sta_translation[Sta_translation['Station_Jp']==Sta_])>0:
                                Final_sta=Sta_translation[Sta_translation['Station_Jp']==Sta_].reset_index(drop=True)['Station_Eng'][0]
                                break
                            else:
                                Phonetic_check=pd.DataFrame()
                                Phonetic_check['Sta']=Sta_translation['Station_Jp']
                                Score=[]
                                for k in range(len(Phonetic_check)):
                                    Score.append(SequenceMatcher(None,Sta,Phonetic_check['Sta'][k]).ratio())
                                Phonetic_check['Score']=Score
                                Phonetic_check=Phonetic_check.sort_values(by=['Score'], ascending=[False])
                                Phonetic_check=Phonetic_check.reset_index(drop=True)
                                Sta=Phonetic_check['Sta'][0]
                                S=[]
                                for k in range(len(Sta_translation)):
                                    if Sta==Sta_translation['Station_Jp'][k]:
                                        S.append(1)
                                    else:
                                        S.append(0)
                                Sta_translation['Check']=S
                                if len(S)>0:
                                    Sta_translation=Sta_translation[Sta_translation['Check']==1].reset_index(drop=True)
                                    Final_sta=Sta_translation['Station_Eng'][0]
                                    break
                                else:
                                    Final_sta=-1
                                break
                else:
                    pos_1=LIST[i-1]
                    pos_2=LIST[i]
                    Sta_=Sta[pos_1:pos_2]
                    if 'ＪＲ' in Sta_ or '線' in Sta_ or '地下鉄' in Sta_ or 'メトロ' in Sta_ or 'ライン' in Sta_:
                        Sta_pos=Sta_.find('「')
                        Sta_pos2=Sta_.find('」')
                        Sta_=Sta_[Sta_pos+1:Sta_pos2]
                        Sta_=Sta_.replace('０','0')
                        Sta_=Sta_.replace('１', '1')
                        Sta_=Sta_.replace('２','2')
                        Sta_=Sta_.replace('３','3')
                        Sta_=Sta_.replace('４','4')
                        Sta_=Sta_.replace('５','5')
                        Sta_=Sta_.replace('６','6')
                        Sta_=Sta_.replace('７','7')
                        Sta_=Sta_.replace('８','8')
                        Sta_=Sta_.replace('９','9')
                        Sta_translation=pd.read_csv('Translation_file.csv',encoding = 'cp932')
                        Sta_translation=Sta_translation[Sta_translation['Municipality_Eng']==Municipality].reset_index(drop=True)
                        Sta_translation=Sta_translation.drop_duplicates(subset='Station_Jp').reset_index(drop=True)
                        Sta_translation=Sta_translation.dropna().reset_index(drop=True)
                        if len(Sta_translation)==1:
                            Final_sta=Sta_translation['Station_Eng'][0]
                            break
                        else:
                            for k in range(len(Sta_translation['Station_Jp'])):
                                if Sta_ in Sta_translation['Station_Jp'][k] and '(' in Sta_translation['Station_Jp'][k] and ')' in Sta_translation['Station_Jp'][k]:
                                    if Sta_[-1]==Sta_translation['Station_Jp'][k][Sta_translation['Station_Jp'][k].find('(')-1]:
                                        Sta_translation=Sta_translation[Sta_translation['Station_Jp']==Sta_translation['Station_Jp'][k]].reset_index(drop=True)
                                        Final_sta=Sta_translation['Station_Eng'][0]
                                        break
                            if len(Sta_translation[Sta_translation['Station_Jp']==Sta_])>0:
                                Final_sta=Sta_translation[Sta_translation['Station_Jp']==Sta_].reset_index(drop=True)['Station_Eng'][0]
                                break
                            else:
                                Phonetic_check=pd.DataFrame()
                                Phonetic_check['Sta']=Sta_translation['Station_Jp']
                                Score=[]
                                for k in range(len(Phonetic_check)):
                                    Score.append(SequenceMatcher(None,Sta,Phonetic_check['Sta'][k]).ratio())
                                Phonetic_check['Score']=Score
                                Phonetic_check=Phonetic_check.sort_values(by=['Score'], ascending=[False])
                                Phonetic_check=Phonetic_check.reset_index(drop=True)
                                Sta=Phonetic_check['Sta'][0]
                                S=[]
                                for k in range(len(Sta_translation)):
                                    if Sta==Sta_translation['Station_Jp'][k]:
                                        S.append(1)
                                    else:
                                        S.append(0)
                                Sta_translation['Check']=S
                                if len(S)>0:
                                    Sta_translation=Sta_translation[Sta_translation['Check']==1].reset_index(drop=True)
                                    Final_sta=Sta_translation['Station_Eng'][0]
                                    break
                                else:
                                    Final_sta=-1
    else:
        Final_sta=-1
    return Final_sta

def Sumo_get_distance_station(HTML_info,Type,District):
    try:
        for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
            if '歩' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
                Pos=i
        Sta_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
        Sta=Sta_elem.text.strip()   

        LIST=[i for i, letter in enumerate(Sta) if letter == '分']
        Distance_station=None

        for i in range(len(LIST)):
            if i==0:
                Ref=Sta[0:LIST[0]+1]
            else:
                Ref=Sta[LIST[i-1]+1:LIST[i]+1]
            if 'バス' not in Ref and ('ＪＲ' in Ref or '線' in Ref or '地下鉄' in Ref):
                Sta_pos=Ref.find('分')
                if Ref[Sta_pos-3] in ['1','2','3','4','5','6','7','8','9']:
                    Distance_station=int(Ref[Sta_pos-3:Sta_pos])
                elif Ref[Sta_pos-2] in ['1','2','3','4','5','6','7','8','9']:
                    Distance_station=int(Ref[Sta_pos-2:Sta_pos])
                elif Ref[Sta_pos-1] in ['1','2','3','4','5','6','7','8','9']:
                    Distance_station=int(Ref[Sta_pos-1:Sta_pos])
                else:
                    Distance_station=int(Ref[Sta_pos])
                break
        if Distance_station==None and Type=='Mansion':
            data=pd.read_csv('Mansion_data.csv')
            data=data[data['District']==District].reset_index(drop=True)
            Distance_station=data['Distance_Nearest_Station(mn)'].max()
        if Distance_station==None and Type=='House':
            data1=pd.read_csv('House_data_1.csv')
            data2=pd.read_csv('House_data_2.csv')
            data3=pd.read_csv('House_data_3.csv')
            data=pd.concat([data1,data2,data3])
            data=data[data['District']==District].reset_index(drop=True)
            Distance_station=data['Distance_Nearest_Station(mn)'].max()
    except:
        Distance_station=-1
    return Distance_station


def Sumo_get_transaction_price(HTML_info):
    Price_elem=HTML_info.find('p',{'class':'mt7 b'}).text.strip()
    if '億'in Price_elem:
        if '・' not in Price_elem and '～' not in Price_elem:
            Pos=Price_elem.find('億')
            if Price_elem[Pos-3] in ['0','1','2','3','4','5','6','7','8','9']:
                Oku=int(Price_elem[Pos-3:Pos])
            elif Price_elem[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Oku=int(Price_elem[Pos-2:Pos])
            else:
                Oku=int(Price_elem[Pos-1])
            Pos2=Price_elem.find('万円')
            if Price_elem[Pos2-4] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos2-3] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos2-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Price_elem[Pos2-4:Pos2])
            elif Price_elem[Pos2-3] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos2-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Price_elem[Pos2-3:Pos2])
            elif Price_elem[Pos2-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Price_elem[Pos2-2:Pos2])
            else:
                Man=int(Price_elem[Pos2-1])
            Final_Price=Oku*100000000+Man*10000
        else:
            if '・' in Price_elem:
                Pos_=Price_elem.find('・')
            else:
                Pos_=Price_elem.find('～')
            Number_1=Price_elem[0:Pos_]
            Number_2=Price_elem[Pos_+1:]
            Pos=Number_1.find('億')
            if Number_1[Pos-3] in ['0','1','2','3','4','5','6','7','8','9']:
                Oku=int(Number_1[Pos-3:Pos])
            elif Number_1[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Oku=int(Number_1[Pos-2:Pos])
            else:
                Oku=int(Number_1[Pos-1])
            Pos2=Number_1.find('万円')
            if Number_1[Pos2-4] in ['0','1','2','3','4','5','6','7','8','9'] and Number_1[Pos2-3] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos2-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_1[Pos2-4:Pos2])
            elif Number_1[Pos2-3] in ['0','1','2','3','4','5','6','7','8','9'] and Number_1[Pos2-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_1[Pos2-3:Pos2])
            elif Number_1[Pos2-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_1[Pos2-2:Pos2])
            else:
                Man=int(Number_1[Pos2-1])
            Number_1=Oku*100000000+Man*10000
            Pos=Number_2.find('億')
            if Number_2[Pos-3] in ['0','1','2','3','4','5','6','7','8','9']:
                Oku=int(Number_2[Pos-3:Pos])
            elif Number_2[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Oku=int(Number_2[Pos-2:Pos])
            else:
                Oku=int(Number_2[Pos-1])
            Pos2=Number_2.find('万円')
            if Number_2[Pos2-4] in ['0','1','2','3','4','5','6','7','8','9'] and Number_2[Pos2-3] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos2-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_2[Pos2-4:Pos2])
            elif Number_2[Pos2-3] in ['0','1','2','3','4','5','6','7','8','9'] and Number_2[Pos2-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_2[Pos2-3:Pos2])
            elif Number_2[Pos2-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_2[Pos2-2:Pos2])
            else:
                Man=int(Number_2[Pos2-1])
            Number_2=Oku*100000000+Man*10000
            Final_Price=(Number_1+Number_2)/2
            
    else:
        if '・' not in Price_elem and '～' not in Price_elem:
            Pos=Price_elem.find('万円')
            if Price_elem[Pos-4] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos-3] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Price_elem[Pos-4:Pos])
            elif Price_elem[Pos-3] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Price_elem[Pos-3:Pos])
            elif Price_elem[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Price_elem[Pos-2:Pos])
            else:
                Man=int(Price_elem[Pos-1])
            Final_Price=Man*10000
        else:
            if '・' in Price_elem:
                Pos_=Price_elem.find('・')
            else:
                Pos_=Price_elem.find('～')
            Number_1=Price_elem[0:Pos_]
            Number_2=Price_elem[Pos_+1:]
            Pos=Number_1.find('万円')
            if Number_1[Pos-4] in ['0','1','2','3','4','5','6','7','8','9'] and Number_1[Pos-3] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_1[Pos-4:Pos])
            elif Number_1[Pos-3] in ['0','1','2','3','4','5','6','7','8','9'] and Number_1[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_1[Pos-3:Pos])
            elif Number_1[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_1[Pos-2:Pos])
            else:
                Man=int(Number_1[Pos-1])
            Number_1=Man*10000
            Pos=Number_2.find('万円')
            if Number_2[Pos-4] in ['0','1','2','3','4','5','6','7','8','9'] and Number_2[Pos-3] in ['0','1','2','3','4','5','6','7','8','9'] and Price_elem[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_2[Pos-4:Pos])
            elif Number_2[Pos-3] in ['0','1','2','3','4','5','6','7','8','9'] and Number_2[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_2[Pos-3:Pos])
            elif Number_2[Pos-2] in ['0','1','2','3','4','5','6','7','8','9']:
                Man=int(Number_2[Pos-2:Pos])
            else:
                Man=int(Number_2[Pos-1])
            Number_2=Man*10000
            Final_Price=(Number_1+Number_2)/2
            
    return Final_Price

def Sumo_get_area(HTML_info):
    try:
        Pos=[]
        for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
            if 'm2' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() and 'バルコニー' not in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() and '面積' not in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
                Pos.append(i)
        if len(Pos)==1:
            Pos=Pos[0]
            Area_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
            Area=Area_elem.text.strip()
            if '～' in Area:
                pos=Area.find('～')
                Number_1=float(Area[0:pos-2])
                pos2=len(Area)
                Number_2=float(Area[pos+1:pos2-2])
                Final_Area=(Number_1+Number_2)/2
                Final_Floor_Area=(Number_1+Number_2)/2
            elif '・' in Area:
                pos=Area.find('・')
                Number_1=float(Area[0:pos-2])
                pos2=len(Area)
                Number_2=float(Area[pos+1:pos2-2])
                Final_Area=(Number_1+Number_2)/2
                Final_Floor_Area=(Number_1+Number_2)/2
            else:
                pos=Area.find('m')
                Final_Area=float(Area[0:pos-1])
                Final_Floor_Area=float(Area[0:pos-1])
        else:
            Pos_r=Pos[0]
            Area_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos_r]
            Area=Area_elem.text.strip()
            if '～' in Area:
                pos_r=Area.find('～')
                Number_1=float(Area[0:pos_r-2])
                pos2=len(Area)
                Number_2=Area[pos_r+1:pos2-2]
                pos_=Number_2.find('m')
                Number_2=float(Number_2[:pos_])
                Final_Floor_Area=(Number_1+Number_2)/2
            elif '・' in Area:
                pos_r=Area.find('・')
                Number_1=float(Area[0:pos_r-2])
                pos2=len(Area)
                Number_2=Area[pos_r+1:pos2-2]
                pos_=Number_2.find('m')
                Number_2=float(Number_2[:pos_])
                Final_Floor_Area=(Number_1+Number_2)/2       
            else:
                pos_r=Area.find('m')
                Final_Floor_Area=float(Area[0:pos_r-1])
            Pos_r=Pos[1]
            Area_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos_r]
            Area=Area_elem.text.strip()
            if '～' in Area:
                pos_r=Area.find('～')
                Number_1=float(Area[0:pos_r-2])
                pos2=len(Area)
                Number_2=Area[pos_r+1:pos2-2]
                pos_=Number_2.find('m')
                Number_2=float(Number_2[:pos_])
                Final_Area=(Number_1+Number_2)/2
            elif '・' in Area:
                pos_r=Area.find('・')
                Number_1=float(Area[0:pos_r-2])
                pos2=len(Area)
                Number_2=Area[pos_r+1:pos2-2]
                pos_=Number_2.find('m')
                Number_2=float(Number_2[:pos_])
                Final_Area=(Number_1+Number_2)/2
            else:
                pos_r=Area.find('m')
                Final_Area=float(Area[0:pos_r-1])
    except:
        Final_Area=-1
        Final_Floor_Area=-1
    return Final_Area,Final_Floor_Area

def Sumo_get_frontage_direction(HTML_info):
    Pos=[]
    for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
        if '幅' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
            Pos.append(i)
    if len(Pos)==0:
        Final_South=0
        Final_North=0
        Final_East=0
        Final_West=0
        Final_South_West=0
        Final_South_East=0
        Final_North_West=0
        Final_North_East=0
    else:
        Front_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos[0]]
        Front=Front_elem.text.strip()
        if '南' in Front and '東' not in Front and '西' not in Front:
            Final_South=1
        else:
            Final_South=0
        if '北' in Front and '東' not in Front and '西' not in Front:
            Final_North=1
        else:
            Final_North=0
        if '東' in Front and '南' not in Front and '北' not in Front:
            Final_East=1
        else:
            Final_East=0
        if '西' in Front and '南' not in Front and '北' not in Front:
            Final_West=1
        else:
            Final_West=0
        if '南' in Front and '西' in Front:
            Final_South_West=1
        else:
            Final_South_West=0
        if '南' in Front and '東' in Front:
            Final_South_East=1
        else:
            Final_South_East=0
        if '北' in Front and '西' in Front:
            Final_North_West=1
        else:
            Final_North_West=0
        if '北' in Front and '東' in Front:
            Final_North_East=1
        else:
            Final_North_East=0        
    return Final_South,Final_North,Final_East,Final_West,Final_South_West,Final_South_East,Final_North_West,Final_North_East

def Sumo_get_frontage_breadth(HTML_info):
    try:
        Pos=[]
        CLASS='w299 bdCell'
        for i in range(len(HTML_info.find_all('td',{'class':CLASS}))):
            if '道路' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or '道幅' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or ('幅' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() and ('北' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or '南' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or '西' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or '東' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip())):
                Pos.append(i)
        if len(Pos)==0:
            CLASS='w290 bdCell'
            for i in range(len(HTML_info.find_all('td',{'class':CLASS}))):
                if '道路' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or'道幅' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or ('幅' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() and ('北' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or '南' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or '西' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip() or '東' in HTML_info.find_all('td',{'class':CLASS})[i].text.strip())):
                    Pos.append(i)
        if len(Pos)==0:
            Final_Frontage=-1
        else:
            Front_elem=HTML_info.find_all('td',{'class':CLASS})[Pos[0]]
            Front=Front_elem.text.strip()
            if '・' in Front:
                pos_r=Front.find('・')
                font_1=Front[:pos_r]
                font_2=Front[pos_r:]
                Number_1=re.findall(r"[-+]?\d*\.\d+|\d+", font_1)
                Number_2=re.findall(r"[-+]?\d*\.\d+|\d+", font_2)
                Final_Frontage=(float(Number_1[0])+float(Number_2[0]))/2
            elif '～' in Front:
                pos_r=Front.find('～')
                font_1=Front[:pos_r]
                font_2=Front[pos_r:]
                Number_1=re.findall(r"[-+]?\d*\.\d+|\d+", font_1)
                Number_2=re.findall(r"[-+]?\d*\.\d+|\d+", font_2)
                Final_Frontage=(float(Number_1[0])+float(Number_2[0]))/2
            else:
                Number=re.findall(r"[-+]?\d*\.\d+|\d+", Front)
                Final_Frontage=float(Number[0])
    except:
        Final_Frontage=-1
    return Final_Frontage

def Sumo_get_Building_coverage_ratio(HTML_info):
    try:
        Pos=None
        for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
            if '率：' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
                Pos=i
        if Pos!=None:
            Cov_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
            Cov=Cov_elem.text.strip()
            Position_1=[pos for pos, char in enumerate(Cov) if char == '：'][0]
            Position_2=[pos for pos, char in enumerate(Cov) if char == '％'][0]
            Final_Cov=float(Cov[Position_1+1:Position_2])
        else:
            for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):      
                if '％' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
                    Pos=i
            Cov_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
            Cov=Cov_elem.text.strip()
            Position=[pos for pos, char in enumerate(Cov) if char == '％'][0]
            Final_Cov=float(Cov[0:Position])
    except:
        Final_Cov=-1
    return Final_Cov

def Sumo_get_Floor_area_ratio(HTML_info):
    try:
        for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
            if '％' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
                Pos=i
        Cov_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
        Cov=Cov_elem.text.strip()
        Position=[pos for pos, char in enumerate(Cov) if char == '％'][1]
        if Cov[Position-3] in ['0','1','2','3','4','5','6','7','8','9']:
            Final_Area_Ratio=float(Cov[Position-3:Position])
        else:
            Final_Area_Ratio=float(Cov[Position-2:Position])
        if Final_Area_Ratio==0:
            Final_Area_ratio=-1
    except:
        Final_Area_Ratio=-1
    return Final_Area_Ratio

def Sumo_get_Building_Structure(HTML_info):
    for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
        if 'RC' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or '木造' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or 'SRC' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or 'SRC' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or '鉄骨造' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or 'ブロック造' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or '軽量鉄骨造' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
            Pos=i
    Struc_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
    Struc=Struc_elem.text.strip()
    if 'RC' in Struc and 'SRC' not in Struc:
        Final_RC=1
    else:
        Final_RC=0
    if '木造' in Struc:
        Final_W=1
    else:
        Final_W=0
    if 'SRC' in Struc or 'SRC' in Struc:
        Final_SRC=1
    else:
        Final_SRC=0
    if '鉄骨造' in Struc and '軽量' not in Struc:
        Final_S=1
    else:
        Final_S=0
    if 'ブロック造' in Struc:
        Final_B=1
    else:
        Final_B=0
    if '軽量鉄骨造' in Struc:
        Final_LS=1
    else:
        Final_LS=0
    return Final_RC,Final_W,Final_SRC,Final_S,Final_B,Final_LS

def Sumo_get_Building_age(HTML_info):
    try:
        for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
            if '年' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() and '月' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() and '完了' not in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() and '予定' not in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
                Pos=i
        Age_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
        Age=Age_elem.text.strip()
        Final_Age=2021-int(Age[0:4])
    except:
        Final_Age=-1
    return Final_Age

def Sumo_get_Layout(HTML_info):
    for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
        if 'LD' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or '1R' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or 'K' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip():
            Pos=i
    Layout_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos]
    Layout_elem=Layout_elem.text.strip()
    
    if '1K' in Layout_elem:
        UnK=1
    else:
        UnK=0
        
    if '2K' in Layout_elem:
        DeuxK=1
    else:
        DeuxK=0
    if '3K' in Layout_elem:
        TroisK=1
    else:
        TroisK=0
    if '4K' in Layout_elem:
        QuatreK=1
    else:
        QuatreK=0
    if '5K' in Layout_elem:
        CinqK=1
    else:
        CinqK=0
    if '1DK' in Layout_elem:
        UnDK=1
    else:
        UnDK=0
    if '2DK' in Layout_elem:
        DeuxDK=1
    else:
        DeuxDK=0
    if '3DK' in Layout_elem:
        TroisDK=1
    else:
        TroisDK=0
    if '4DK' in Layout_elem:
        QuatreDK=1
    else:
        QuatreDK=0
    if '5DK' in Layout_elem:
        CinqDK=1
    else:
        CinqDK=0
    if '6DK' in Layout_elem:
        SixDK=1
    else:
        SixDK=0
    if '7DK' in Layout_elem:
        SeptDK=1
    else:
        SeptDK=0
    if '1LDK' in Layout_elem:
        UnLDK=1
    else:
        UnLDK=0
    if '2LDK' in Layout_elem:
        DeuxLDK=1
    else:
        DeuxLDK=0
    if '3LDK' in Layout_elem:
        TroisLDK=1
    else:
        TroisLDK=0
    if '4LDK' in Layout_elem:
        QuatreLDK=1
    else:
        QuatreLDK=0
    if '5LDK' in Layout_elem:
        CinqLDK=1
    else:
        CinqLDK=0
    if '6LDK' in Layout_elem:
        SixLDK=1
    else:
        SixLDK=0
    if '7LDK' in Layout_elem:
        SeptLDK=1
    else:
        SeptLDK=0
    if '8LDK' in Layout_elem:
        HuitLDK=1
    else:
        HuitLDK=0
    if '1R' in Layout_elem:
        UnR=1
    else:
        UnR=0
        
    return UnK,DeuxK,TroisK,QuatreK,CinqK,UnDK,DeuxDK,TroisDK,QuatreDK,CinqDK,SixDK,SeptDK,UnLDK,DeuxLDK,TroisLDK,QuatreLDK,CinqLDK,SixLDK,SeptLDK,HuitLDK,UnR


def Sumo_get_Renovation(HTML_info):
    try:
        Pos=[]
        for i in range(len(HTML_info.find_all('td',{'class':'w299 bdCell'}))):
            if '完了' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() or '予定' in HTML_info.find_all('td',{'class':'w299 bdCell'})[i].text.strip() :
                Pos.append(i)
        if len(Pos)==0:
            Renov_None=1
            Renov_Done=0
            Renov_plan=0
        else:
            Renov_None=0
            Renov_elem=HTML_info.find_all('td',{'class':'w299 bdCell'})[Pos[0]]
            Renov_elem=Renov_elem.text.strip()
            if '完了' in Renov_elem:
                Renov_Done=1
                Renov_plan=0
            elif '予定' in Renov_elem:
                Renov_Done=0
                Renov_plan=1  
    except:
        Renov_None=1
        Renov_Done=0
        Renov_plan=0
    return Renov_None,Renov_Done,Renov_plan


def Get_result(link,User_type,Method):
    if 'bukkengaiyo' in link:
        link=link
    elif 'kankyo' in link:
        substring=link.split('kankyo',1)
        link=substring[0]+'bukkengaiyo/'
    elif 'tenpo' in link:       
        substring=link.split('tenpo',1)
        link=substring[0]+'bukkengaiyo/'
    elif 'kuchikomi' in link:        
        substring=link.split('kuchikomi',1)
        link=substring[0]+'bukkengaiyo/'
    else:
        link=link+'bukkengaiyo/'

    Request_Result=Sumo_get_html_info(link)
    HTML_info=Request_Result[0]
    Type=Request_Result[1]

    Prefecture=Sumo_get_prefecture(HTML_info)
    Result_Municipality=Sumo_get_municipality(HTML_info)
    Municipality=Result_Municipality[1]
    District=Sumo_get_district(HTML_info,Result_Municipality[0],Result_Municipality[1])
    Station=Sumo_get_station(HTML_info,Result_Municipality[1])
    if Prefecture==-1 or Municipality==-1 or District==-1 or Station==-1:
        Message='Unfortunately, we could not get the location of the real estate property you are looking for. Our models are probably not yet ready to be deployed in your area.'
        Prediction_html=0
        Prediction_Warning=0
        Confidence_index=0
        Ref_1_html=0
        Ref_2_html=0
        Distance_Station_html=0
        Area_html=0
        Building_ratio_html=0
        Floor_ratio_html=0
        Building_age_html=0
        Floor_area_html=0
        Frontage_breadth_html=0
        Frontage_direction_html=0
        Building_structure_html=0
        District_html=0
        Layout_html=0
        Renovation_html=0
        Evaluation_Summary=0
    else:
        Distance_station=Sumo_get_distance_station(HTML_info,Type,District)
        Price=Sumo_get_transaction_price(HTML_info)
        Area=Sumo_get_area(HTML_info)
        City_planning=Sumo_get_region_city_planning(HTML_info)
        Building_ratio=Sumo_get_Building_coverage_ratio(HTML_info)
        Floor_ratio=Sumo_get_Floor_area_ratio(HTML_info)
        Building_structure=Sumo_get_Building_Structure(HTML_info)
        Building_age=Sumo_get_Building_age(HTML_info)
        if Type=='House':
            Frontage_direction=Sumo_get_frontage_direction(HTML_info)
            Frontage_breadth=Sumo_get_frontage_breadth(HTML_info)
        else:
            Layout=Sumo_get_Layout(HTML_info)
            Renovation=Sumo_get_Renovation(HTML_info)
        if Type=='House':
            Model_result=House_model_result
        else:
            Model_result=Mansion_model_result

        Model_result_=Model_result[Model_result['Municipality']==Municipality].reset_index(drop=True)
        if Type=='House':
            if Model_result_['Prefecture_Accuracy'][0]<Model_result_['Municipality_Accuracy'][0]:
                Model_accuracy=Model_result_['Prefecture_Accuracy'][0]
                Coefficient=Model_result_['Prefecture_Coefficient'][0]
                Model=pickle.load(open('House_Prefecture_'+str(Prefecture)+'.sav','rb'))
                Column_frame=pd.read_csv('House_Prefecture_'+str(Prefecture)+'.csv')
                Column_frame=Column_frame.drop(['Unnamed: 0'],axis=1)
            else:
                Model_accuracy=Model_result_['Municipality_Accuracy'][0]
                Coefficient=Model_result_['Municipality_Coefficient'][0]
                Model=pickle.load(open('House_Municipality_'+str(Municipality)+'.sav','rb'))
                Column_frame=pd.read_csv('House_Municipality_'+str(Municipality)+'.csv')
                Column_frame=Column_frame.drop(['Unnamed: 0'],axis=1)
        else:
            if Model_result_['General_Accuracy'][0]<Model_result_['Prefecture_Accuracy'][0] and Model_result_['General_Accuracy'][0]<Model_result_['Municipality_Accuracy'][0]:
                Model_accuracy=Model_result_['General_Accuracy'][0]
                Coefficient=Model_result_['General_Coefficient'][0]
                if Prefecture in NORTH:
                    Title='NORTH'
                elif Prefecture in KANTO_1:
                    Title='KANTO_1'
                elif Prefecture in KANTO_2:
                    Title='KANTO_2'
                elif Prefecture in CENTRAL:
                    Title='CENTRAL'
                elif Prefecture in KANSAI_1:
                    Title='KANSAI_1'
                elif Prefecture in KANSAI_2:
                    Title='KANSAI_2'
                elif Prefecture in WEST:
                    Title='WEST'
                elif Prefecture in SHIKOKU:
                    Title='SHIKOKU'
                else:
                    Title='KYUSHU' 
                Model=pickle.load(open('Mansion_'+str(Title)+'.sav','rb'))
                Column_frame=pd.read_csv('Mansion_'+str(Title)+'.csv')
                Column_frame=Column_frame.drop(['Unnamed: 0'],axis=1)
            elif Model_result_['Prefecture_Accuracy'][0]<Model_result_['Municipality_Accuracy'][0]:
                Model_accuracy=Model_result_['Prefecture_Accuracy'][0]
                Coefficient=Model_result_['Prefecture_Coefficient'][0]
                Model=pickle.load(open('Mansion_Prefecture_'+str(Prefecture)+'.sav','rb'))
                Column_frame=pd.read_csv('Mansion_Prefecture_'+str(Prefecture)+'.csv')
                Column_frame=Column_frame.drop(['Unnamed: 0'],axis=1)
            else:
                Model_accuracy=Model_result_['Municipality_Accuracy'][0]
                Coefficient=Model_result_['Municipality_Coefficient'][0]
                Model=pickle.load(open('Mansion_Municipality_'+str(Municipality)+'.sav','rb'))
                Column_frame=pd.read_csv('Mansion_Municipality_'+str(Municipality)+'.csv')
                Column_frame=Column_frame.drop(['Unnamed: 0'],axis=1)       

        if sum(1 for s in list(Column_frame.columns) if 'Prefecture_' in s)==1:
            filter_col = [col for col in Column_frame if col.startswith('Prefecture_')]
            Column_frame[filter_col]=1
        else:
            Column_frame['Prefecture_'+str(Prefecture)]=1
        if sum(1 for s in list(Column_frame.columns) if 'Municipality_' in s)==1:
            filter_col = [col for col in Column_frame if col.startswith('Municipality_')]
            Column_frame[filter_col]=1
        else:
            Column_frame['Municipality_'+str(Municipality)]=1
        if sum(1 for s in list(Column_frame.columns) if 'District_' in s)==1:
            filter_col = [col for col in Column_frame if col.startswith('District_')]
            Column_frame[filter_col]=1
        else:
            Column_frame['District_'+str(District)]=1
        if sum(1 for s in list(Column_frame.columns) if 'Nearest_Station_' in s)==1:
            filter_col = [col for col in Column_frame if col.startswith('Nearest_Station_')]
            Column_frame[filter_col]=1
        else:
            Column_frame['Nearest_Station_'+str(Station)]=1
        if Distance_station!=-1:
            Column_frame['Distance_Nearest_Station(mn)']=Distance_station
        else:
            Column_frame['Distance_Nearest_Station(mn)']=10
        if Area[0]!=-1:
            Column_frame['Area(m^2)']=Area[0]
        else:
            Column_frame['Area(m^2)']=60
        if Building_ratio!=-1:
            Column_frame['Maximus Building Coverage Ratio(%)']=Building_ratio
        else:
            Column_frame['Maximus Building Coverage Ratio(%)']=60
        if Floor_ratio!=-1:
            Column_frame['Maximus Floor-area Ratio(%)']=Floor_ratio
        else:
            Column_frame['Maximus Floor-area Ratio(%)']=60
        if Building_age!=-1:
            Column_frame['Building_Age']=Building_age
        else:
            Column_frame['Building_Age']=5
        if sum(1 for s in list(Column_frame.columns) if 'City Planning_' in s)==1:
            filter_col = [col for col in Column_frame if col.startswith('City Planning_')]
            Column_frame[filter_col]=1
        else:
            if 'City Planning_Category I Residential Zone' in list(Column_frame.columns):
                Column_frame['City Planning_Category I Residential Zone']=City_planning[1]
            if 'City Planning_Category I Exclusively Low-story Residential Zone' in list(Column_frame.columns):
                Column_frame['City Planning_Category I Exclusively Low-story Residential Zone']=City_planning[0]
            if 'City Planning_Commercial Zone' in list(Column_frame.columns):
                Column_frame['City Planning_Commercial Zone']=City_planning[9]
            if 'City Planning_Neighborhood Commercial Zone' in list(Column_frame.columns):
                Column_frame['City Planning_Neighborhood Commercial Zone']=City_planning[8] 
            if 'City Planning_Category I Exclusively Medium-high Residential Zone' in list(Column_frame.columns):
                Column_frame['City Planning_Category I Exclusively Medium-high Residential Zone']=City_planning[2] 
            if 'City Planning_Industrial Zone' in list(Column_frame.columns):
                Column_frame['City Planning_Quasi-industrial Zone']=City_planning[6]
            if 'City Planning_Category II Residential Zone' in list(Column_frame.columns):
                Column_frame['City Planning_Category II Residential Zone']=City_planning[7]
            if 'City Planning_Urbanization Control Area' in list(Column_frame.columns):
                Column_frame['City Planning_Urbanization Control Area']=City_planning[4]
            if 'City Planning_Quasi-residential Zone' in list(Column_frame.columns):
                Column_frame['City Planning_Quasi-residential Zone']=City_planning[12]
            if 'City_Planning_Category II Exclusively Medium-high Residential Zone' in list(Column_frame.columns):
                Column_frame['City_Planning_Category II Exclusively Medium-high Residential Zone']=City_planning[3]
            if 'City_Planning_Category II Exclusively Low-story Residential Zone' in list(Column_frame.columns):
                Column_frame['City_Planning_Category II Exclusively Low-story Residential Zone']=City_planning[11]
            if 'City_Planning_Exclusively Industrial Zone' in list(Column_frame.columns):
                Column_frame['City_Planning_Exclusively Industrial Zone']=City_planning[10]
            if 'City_Planning_Quasi-city Planning Area' in list(Column_frame.columns):
                Column_frame['City_Planning_Quasi-city Planning Area']=City_planning[13]
            if 'City_Planning_Non-divided City Planning Area' in list(Column_frame.columns):
                Column_frame['City_Planning_Non-divided City Planning Area']=City_planning[5]
            if 'City_Planning_Outside City Planning Area' in list(Column_frame.columns):
                Column_frame['City_Planning_Outside City Planning Area']=City_planning[14]

        if sum(1 for s in list(Column_frame.columns) if 'structure' in s)==1:
            filter_col = [col for col in Column_frame if col.startswith('structure')]
            Column_frame[filter_col]=1
        else:
            if 'Building_structure_RC' in list(Column_frame.columns):
                Column_frame['Building_structure_RC']=Building_structure[0]
            if 'Building_structure_W' in list(Column_frame.columns):
                Column_frame['Building_structure_W']=Building_structure[1]
            if 'Building_structure_SRC' in list(Column_frame.columns):
                Column_frame['Building_structure_SRC']=Building_structure[2]
            if 'Building_structure_S' in list(Column_frame.columns):
                Column_frame['Building_structure_S']=Building_structure[3]
            if 'Building_structure_B' in list(Column_frame.columns):
                Column_frame['Building_structure_B']=Building_structure[4]
            if 'Building_structure_LS' in list(Column_frame.columns):
                Column_frame['Building_structure_LS']=Building_structure[5]

        if Type=='House':
            if Area[1]!=-1:
                Column_frame['Total floor area(m^2)']=Area[1]
            else:
                Column_frame['Total floor area(m^2)']=60
            if Frontage_breadth!=-1:
                Column_frame['Frontage_Road_Breadth(m)']=Frontage_breadth
            else:
                Column_frame['Frontage_Road_Breadth(m)']=5
            if sum(1 for s in list(Column_frame.columns) if 'Region' in s)==1:
                filter_col = [col for col in Column_frame if col.startswith('Region')]
                Column_frame[filter_col]=1
            else:
                if 'Region_Commercial Area' in list(Column_frame.columns):
                    Column_frame['Region_Commercial Area']=City_planning[16]
                if 'Region_Industrial Area' in list(Column_frame.columns):
                    Column_frame['Region_Industrial Area']=City_planning[17]
                if 'Region_Residential Area' in list(Column_frame.columns):
                    Column_frame['Region_Residential Area']=City_planning[18]
            if sum(1 for s in list(Column_frame.columns) if 'Frontage_Road_Direction' in s)==1:
                filter_col = [col for col in Column_frame if col.startswith('Frontage_Road_Direction')]
                Column_frame[filter_col]=1
            else:
                if 'Frontage_Road_Direction_North' in list(Column_frame.columns):
                    Column_frame['Frontage_Road_Direction_North']=Frontage_direction[1]
                if 'Frontage_Road_Direction_South' in list(Column_frame.columns):
                    Column_frame['Frontage_Road_Direction_South']=Frontage_direction[0]
                if 'Frontage_Road_Direction_East' in list(Column_frame.columns):
                    Column_frame['Frontage_Road_Direction_East']=Frontage_direction[2]
                if 'Frontage_Road_Direction_West' in list(Column_frame.columns):
                    Column_frame['Frontage_Road_Direction_West']=Frontage_direction[3]
                if 'Frontage_Road_Direction_Southwest' in list(Column_frame.columns):
                    Column_frame['Frontage_Road_Direction_Southwest']=Frontage_direction[4]
                if 'Frontage_Road_Direction_Southeast' in list(Column_frame.columns):
                    Column_frame['Frontage_Road_Direction_Southeast']=Frontage_direction[5]
                if 'Frontage_Road_Direction_Northwest' in list(Column_frame.columns):
                    Column_frame['Frontage_Road_Direction_Northwest']=Frontage_direction[6]
                if 'Frontage_Road_Direction_Northeast' in list(Column_frame.columns):
                    Column_frame['Frontage_Road_Direction_Northeast']=Frontage_direction[7]

                for i in ['Area(m^2)','Total floor area(m^2)','Frontage_Road_Breadth(m)']:
                    Column_frame[i]=np.log(Column_frame[i])   
        else:
            if sum(1 for s in list(Column_frame.columns) if 'Layout' in s)==1:
                filter_col = [col for col in Column_frame if col.startswith('Layout')]
                Column_frame[filter_col]=1
            else:
                if 'Layout_1K' in list(Column_frame.columns):
                    Column_frame['Layout_1K']=Layout[0]
                if 'Layout_2K' in list(Column_frame.columns):
                    Column_frame['Layout_2K']=Layout[1]
                if 'Layout_3K' in list(Column_frame.columns):
                    Column_frame['Layout_3K']=Layout[2]
                if 'Layout_4K' in list(Column_frame.columns):
                    Column_frame['Layout_4K']=Layout[3]
                if 'Layout_5K' in list(Column_frame.columns):
                    Column_frame['Layout_5K']=Layout[4]
                if 'Layout_1DK' in list(Column_frame.columns):
                    Column_frame['Layout_1DK']=Layout[5]
                if 'Layout_2DK' in list(Column_frame.columns):
                    Column_frame['Layout_2DK']=Layout[6]
                if 'Layout_3DK' in list(Column_frame.columns):
                    Column_frame['Layout_3DK']=Layout[7]
                if 'Layout_4DK' in list(Column_frame.columns):
                    Column_frame['Layout_4DK']=Layout[8]
                if 'Layout_5DK' in list(Column_frame.columns):
                    Column_frame['Layout_5DK']=Layout[9]
                if 'Layout_6DK' in list(Column_frame.columns):
                    Column_frame['Layout_6DK']=Layout[10]
                if 'Layout_7DK' in list(Column_frame.columns):
                    Column_frame['Layout_7DK']=Layout[11]
                if 'Layout_1LDK' in list(Column_frame.columns):
                    Column_frame['Layout_1LDK']=Layout[12]
                if 'Layout_2LDK' in list(Column_frame.columns):
                    Column_frame['Layout_2LDK']=Layout[13]
                if 'Layout_3LDK' in list(Column_frame.columns):
                    Column_frame['Layout_3LDK']=Layout[14]
                if 'Layout_4LDK' in list(Column_frame.columns):
                    Column_frame['Layout_4LDK']=Layout[15]
                if 'Layout_5LDK' in list(Column_frame.columns):
                    Column_frame['Layout_5LDK']=Layout[16]
                if 'Layout_6LDK' in list(Column_frame.columns):
                    Column_frame['Layout_6LDK']=Layout[17]
                if 'Layout_7LDK' in list(Column_frame.columns):
                    Column_frame['Layout_7LDK']=Layout[18]
                if 'Layout_8LDK' in list(Column_frame.columns):
                    Column_frame['Layout_8LDK']=Layout[19]
                if 'Layout_1R' in list(Column_frame.columns):
                    Column_frame['Layout_1R']=Layout[20]

            if sum(1 for s in list(Column_frame.columns) if 'Renovation' in s)==1:
                filter_col = [col for col in Column_frame if col.startswith('Renovation')]
                Column_frame[filter_col]=1
            else:
                if 'Renovation_Not yet' in list(Column_frame.columns):
                    Column_frame['Renovation_Not yet']=Renovation[2]
                if 'Renovation_Done' in list(Column_frame.columns):
                    Column_frame['Renovation_Done']=Renovation[1]
                if 'Renovation_Unknown' in list(Column_frame.columns):
                    Column_frame['Renovation_Unknown']=Renovation[0]
                Column_frame['Area(m^2)']=np.log(Column_frame['Area(m^2)']) 
        X=np.array(Column_frame)
        Pred=Model.predict(X)
        Final_pred=np.exp(Pred)[0]*Coefficient
        plt.figure()
        sns.set(style="white", color_codes=True)
        data={'Type':['Current Price','Market Price prediction'],'Price':[Price,Final_pred]}
        ax=sns.barplot(x="Price", y="Type", data=data,palette="light:#5A9")
        ax.set_yticklabels(data['Type'], size = 15) 
        for p in ax.patches:
            ax.annotate(text=locale.format("%d", p.get_width(), grouping=True)+' JPY', xy=(p.get_width()/2, p.get_y()+p.get_height()/2),
                    xytext=(5, 0), textcoords='offset points', ha="center", va="center",size=15)
        ax.set(xticks=[])
        encoded = fig_to_base64(ax)
        Prediction_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))
        
        if Type=='House':
            if Distance_station==-1 or Area[0]==-1 or Area[1]==-1 or Building_ratio==-1 or Floor_ratio==-1 or Building_age==-1 or Frontage_breadth==-1:
                Warning_1='The following features are missing from the link. Please note that an arbitrary average value have been inserted instead to make the prediction: '
                Feature_list=[]
                if Distance_station==-1:
                    Feature_list.append('Walking distance to nearest station(mn)')
                if Area[0]==-1:
                    Feature_list.append('Property area (m2)')
                if Area[1]==-1:
                    Feature_list.append('Property floor area (m2)')
                if Building_ratio==-1:
                    Feature_list.append('Building ratio (%)')
                if Floor_ratio==-1:
                    Feature_list.append('Floor area ratio (%)')
                if Building_age==-1:
                    Feature_list.append('Building age (years)')
                if Frontage_breadth==-1:
                    Feature_list.append('Frontage breadth (m)')
                if len(Feature_list)==1:
                    Warning_2=Feature_list[0]
                else:
                    for a in range(len(Feature_list)):
                        if a==0:
                            Warning_2=Feature_list[a]
                        else:
                            Warning_2=Warning_2+', '+Feature_list[a]
                Prediction_Warning=Warning_1+': '+Warning_2
            else:
                Prediction_Warning=0
        else:
            if Distance_station==-1 or Area[0]==-1 or Building_ratio==-1 or Floor_ratio==-1 or Building_age==-1:
                Warning_1='The following features are missing from the link. Please note that an arbitrary average value have been inserted instead to make the prediction: '
                Feature_list=[]
                if Distance_station==-1:
                    Feature_list.append('Walking distance to nearest station(mn)')
                if Area[0]==-1:
                    Feature_list.append('Property area (m2)')
                if Building_ratio==-1:
                    Feature_list.append('Building ratio (%)')
                if Floor_ratio==-1:
                    Feature_list.append('Floor area ratio (%)')
                if Building_age==-1:
                    Feature_list.append('Building age (years)')
                if len(Feature_list)==1:
                    Warning_2=Feature_list[0]
                else:
                    for a in range(len(Feature_list)):
                        if a==0:
                            Warning_2=Feature_list[a]
                        else:
                            Warning_2=Warning_2+', '+Feature_list[a]
                Prediction_Warning=Warning_1+': '+Warning_2
            else:
                Prediction_Warning=0        
                
        if Final_pred==Price:
            Message='Listed price and predicted market price are the same'
        elif Final_pred>Price:
            diff=round(Final_pred-Price,0)
            diff=locale.format("%d", diff, grouping=True)
            diff_p=round((Final_pred-Price)/Price*100,2)
            if User_type=='Buyer':
                Message='Good price to buy! Listed price is under the estimated market price  by '+str(diff)+' JPY ('+str(diff_p)+'%)'
            else:
                Message='You could probably sell for more. Your listed price is under the estimated market price  by '+str(diff)+' JPY ('+str(diff_p)+'%)'
        else:
            diff=round(Price-Final_pred,0)
            diff=locale.format("%d", diff, grouping=True)
            diff_p=round((Price-Final_pred)/Price*100,2)
            if User_type=='Buyer':
                Message='There is room for negociation to lower the price. Listed price is over the estimated price by '+str(diff)+' JPY ('+str(diff_p)+'%)'
            else:
                Message='You might have some difficulties to sell. Your listed price is over the estimated market price by '+str(diff)+' JPY ('+str(diff_p)+'%)'

        if Model_accuracy<0.12:
            Confidence_index='A'
        elif Model_accuracy<0.2:
            Confidence_index='B'
        elif Model_accuracy<0.3:
            Confidence_index='C'
        else:
            Confidence_index='D'

        #Search historics
        if Type=='House':
            data1=pd.read_csv('House_data_1.csv')
            data2=pd.read_csv('House_data_2.csv')
            data3=pd.read_csv('House_data_3.csv')
            ref_data=pd.concat([data1,data2,data3])
        else:
            ref_data=pd.read_csv('Mansion_data.csv')
        ref_data=ref_data[ref_data['Municipality']==str(Municipality)].reset_index(drop=True)
        ref_data['Sales_transaction_year']=ref_data['Year'].astype(str)
        YEAR=[]
        for i in range(len(ref_data)):
            YEAR.append(int(ref_data['Sales_transaction_year'][i][:4]))
        ref_data['Sales_transaction_year']=YEAR

        Structure=[]
        for i in range(len(ref_data)):
            if ref_data['Building_structure_RC'][i]==1:
                Structure.append('RC')
            elif ref_data['Building_structure_SRC'][i]==1:
                Structure.append('SRC')
            elif ref_data['Building_structure_S'][i]==1:
                Structure.append('S')
            elif ref_data['Building_structure_B'][i]==1:
                Structure.append('B')
            elif ref_data['Building_structure_W'][i]==1:
                Structure.append('W')
            elif ref_data['Building_structure_LS'][i]==1:
                Structure.append('LS')
        ref_data['Building_Structure']=Structure

        Score_=[]
        for i in range(len(ref_data)):
            Score=[]
            if ref_data['Building_Structure'][i]=='RC' and Building_structure[0]==1:
                Score.append(5)
            elif ref_data['Building_Structure'][i]=='W' and Building_structure[1]==1:
                Score.append(5)
            elif ref_data['Building_Structure'][i]=='SRC' and Building_structure[2]==1:
                Score.append(5)
            elif ref_data['Building_Structure'][i]=='S' and Building_structure[3]==1:
                Score.append(5)
            elif ref_data['Building_Structure'][i]=='B' and Building_structure[4]==1:
                Score.append(5)
            elif ref_data['Building_Structure'][i]=='LS' and Building_structure[5]==1:
                Score.append(5) 
            if ref_data['District'][i]==District:
                Score.append(10)
            if ref_data['Nearest_Station'][i]==Station:
                Score.append(8)
            if abs(ref_data['Distance_Nearest_Station(mn)'][i]-Distance_station)>28:
                Score.append(0)
            else:
                Score.append(7-abs(ref_data['Distance_Nearest_Station(mn)'][i]-Distance_station)/4)
            if abs(ref_data['Area(m^2)'][i]-Area[0])>40:
                Score.append(0)
            else:
                Score.append(10-abs(ref_data['Area(m^2)'][i]-Area[0])/4)
            if abs(ref_data['Maximus Building Coverage Ratio(%)'][i]-Building_ratio)>40:
                Score.append(0)
            else:
                Score.append(4-abs(ref_data['Maximus Building Coverage Ratio(%)'][i]-Building_ratio)/10)
            if abs(ref_data['Maximus Floor-area Ratio(%)'][i]-Floor_ratio)>80:
                Score.append(0)
            else:
                Score.append(4-abs(ref_data['Maximus Floor-area Ratio(%)'][i]-Floor_ratio)/20)
            if abs(ref_data['Building_Age'][i]-Building_age)>14:
                Score.append(0)
            else:
                Score.append(7-abs(ref_data['Building_Age'][i]-Building_age)/2)
            if int(str(ref_data['Year'][i])[:4])<2012:  
                Score.append(0)
            else:
                Score.append(8-(2020-int(str(ref_data['Year'][i])[:4])))
            if Type=='House':
                if abs(ref_data['Total floor area(m^2)'][i]-Area[1])>20:
                    Score.append(0)
                else:
                    Score.append(5-abs(ref_data['Total floor area(m^2)'][i]-Area[1])/4)
                for k in ref_data['Frontage_Road_Direction'].drop_duplicates():
                    if Column_frame['Frontage_Road_Direction_'+str(k)][0]==1:
                        Frontage_direction=str(k)
                        if ref_data['Frontage_Road_Direction'][i]==str(k):
                            Score.append(4)
                            break
                if abs(ref_data['Frontage_Road_Breadth(m)'][i]-Frontage_breadth)>10:
                    Score.append(0)
                else:
                    Score.append(5-abs(ref_data['Frontage_Road_Breadth(m)'][i]-Frontage_breadth)/2)
            else:
                for k in ref_data['Layout'].drop_duplicates():
                    if Column_frame['Layout_'+str(k)][0]==1:
                        Layout=str(k)
                        if ref_data['Layout'][i]==str(k):
                            Score.append(8)
                        else:
                            if 'LDK' in k and 'LDK' in ref_data['Layout'][i]:
                                if 8-abs(int(k[0])-int(ref_data['Layout'][i][0]))*2<0:
                                    Score.append(0)
                                    break
                                else:
                                    Score.append(8-abs(int(k[0])-int(ref_data['Layout'][i][0]))*2)
                                    break
                            elif 'DK' in k and 'DK' in ref_data['Layout'][i]:
                                if 8-abs(int(k[0])-int(ref_data['Layout'][i][0]))*2<0:
                                    Score.append(0)
                                    break
                                else:
                                    Score.append(8-abs(int(k[0])-int(ref_data['Layout'][i][0]))*2)
                                    break
                            else:
                                Score.append(0)
                                break
                for k in ref_data['Renovation'].drop_duplicates():
                    if Column_frame['Renovation_'+str(k)][0]==1:
                        Renovation=str(k)
                        if ref_data['Renovation'][i]==str(k):
                            Score.append(4)
                            break

            Score_.append(np.sum(Score))
        ref_data['Score']=Score_
        ref_data=ref_data.sort_values(by='Score', ascending=False).reset_index(drop=True)

        Price_=[]
        for i in range(len(ref_data)):
            Price_.append(locale.format("%d", ref_data['Transaction-price(total)'][i], grouping=True)+' JPY')
        ref_data['Transaction-price(total)']=Price_

        if Building_structure[0]==1:
            Structure='RC'
        elif Building_structure[1]==1:
            Structure='W'
        elif Building_structure[2]==1:
            Structure='SRC'
        elif Building_structure[3]==1:
            Structure='S'
        elif Building_structure[4]==1:
            Structure='B'
        elif Building_structure[5]==1:
            Structure='LS'

        ref_data['Transaction price(JPY)']=ref_data['Transaction-price(total)']
        ref_data['Distance to nearest station (mn)']=ref_data['Distance_Nearest_Station(mn)']
        ref_data['Property area(m2)']=ref_data['Area(m^2)']
        ref_data['Building structure']=ref_data['Building_Structure']
        ref_data['Maximum Building Coverage Ratio(%)']=ref_data['Maximus Building Coverage Ratio(%)']
        ref_data['Maximum Floor-area Ratio(%)']=ref_data['Maximus Floor-area Ratio(%)']
        ref_data['Building_Structure']=ref_data['Building structure']
        ref_data['Building age(years)']=ref_data['Building_Age']

        if len(ref_data)>5:
            ref_data=ref_data[:5]
        if len(ref_data)==5:
            ref_data['Similarity ranking']=['①','②','③','④','⑤']
        elif len(ref_data)==4:
            ref_data['Similarity ranking']=['①','②','③','④']
        elif len(ref_data)==3:
            ref_data['Similarity ranking']=['①','②','③']
        elif len(ref_data)==2:
            ref_data['Similarity ranking']=['①','②']
        elif len(ref_data)==1:
            ref_data['Similarity ranking']=['①']
        
        if Type=='House':
            ref_data_1=ref_data[['Similarity ranking','Transaction price(JPY)','Sales_transaction_year','Municipality','District','Nearest_Station','Distance to nearest station (mn)',
                              'Property area(m2)','Total floor area(m^2)']]
            ref_data_2=ref_data[['Similarity ranking','Maximum Building Coverage Ratio(%)','Maximum Floor-area Ratio(%)',
                                 'Building structure','Building age(years)'
                               ,'Frontage_Road_Direction','Frontage_Road_Breadth(m)']]
            for i in ['Maximum Building Coverage Ratio(%)','Maximum Floor-area Ratio(%)','Frontage_Road_Breadth(m)']:
                ref_data_2[i]=ref_data_2[i].astype(int)

            ref_data_1=ref_data_1.style.apply(lambda x: ['background: orange' if v >2018 else '' for v in x], axis = 1,subset=['Sales_transaction_year']).apply(lambda x: ['background: red' if v ==Municipality else '' for v in x], axis = 1,subset=['Municipality']).apply(lambda x: ['background: red' if v ==District else '' for v in x], axis = 1,subset=['District']).apply(lambda x: ['background: red' if v ==Station else '' for v in x], axis = 1,subset=['Nearest_Station']).apply(lambda x: ['background: red' if abs(v-Distance_station)<2 else '' for v in x], axis = 1,subset=['Distance to nearest station (mn)']).apply(lambda x: ['background: orange' if abs(v-Distance_station)>1 and abs(v-Distance_station)<6 else '' for v in x], axis = 1,subset=['Distance to nearest station (mn)']).apply(lambda x: ['background: red' if abs(v-Area[0])<6 else '' for v in x], axis = 1,subset=['Property area(m2)']).apply(lambda x: ['background: orange' if abs(v-Area[0])>5 and abs(v-Area[0])<21  else '' for v in x], axis = 1,subset=['Property area(m2)']).apply(lambda x: ['background: red' if abs(v-Area[1])<6 else '' for v in x], axis = 1,subset=['Total floor area(m^2)']).apply(lambda x: ['background: orange' if abs(v-Area[1])>5 and abs(v-Area[1])<21  else '' for v in x], axis = 1,subset=['Total floor area(m^2)']).set_properties(**{'text-align': 'center'}).set_properties(**{'text-align': 'center'}).hide_index().set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
            ref_data_2=ref_data_2.style.apply(lambda x: ['background: red' if abs(v-Building_ratio)<6 else '' for v in x], axis = 1,subset=['Maximum Building Coverage Ratio(%)']).apply(lambda x: ['background: orange' if abs(v-Building_ratio)>5 and abs(v-Building_ratio)<21  else '' for v in x], axis = 1,subset=['Maximum Building Coverage Ratio(%)']).apply(lambda x: ['background: red' if abs(v-Floor_ratio)<6 else '' for v in x], axis = 1,subset=['Maximum Floor-area Ratio(%)']).apply(lambda x: ['background: orange' if abs(v-Floor_ratio)>5 and abs(v-Floor_ratio)<21  else '' for v in x], axis = 1,subset=['Maximum Floor-area Ratio(%)']).apply(lambda x: ['background: red' if v ==Structure else '' for v in x], axis = 1,subset=['Building structure']).apply(lambda x: ['background: red' if abs(v-Building_age)<2 else '' for v in x], axis = 1,subset=['Building age(years)']).apply(lambda x: ['background: orange' if abs(v-Building_age)>1 and abs(v-Building_age)<6 else '' for v in x], axis = 1,subset=['Building age(years)']).apply(lambda x: ['background: red' if v=='Frontage_direction'  else '' for v in x], axis = 1,subset=['Frontage_Road_Direction']).apply(lambda x: ['background: red' if abs(v-Frontage_breadth)<2  else '' for v in x], axis = 1,subset=['Frontage_Road_Breadth(m)']).apply(lambda x: ['background: orange' if abs(v-Frontage_breadth)>1 and abs(v-Frontage_breadth)<4   else '' for v in x], axis = 1,subset=['Frontage_Road_Breadth(m)']).set_properties(**{'text-align': 'center'}).set_properties(**{'text-align': 'center'}).hide_index().set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
        
        else:
            ref_data_1=ref_data[['Transaction price(JPY)','Sales_transaction_year','Municipality','District',
                                 'Nearest_Station','Distance to nearest station (mn)',
                              'Property area(m2)']]
            ref_data_2=ref_data[['Maximum Building Coverage Ratio(%)','Maximum Floor-area Ratio(%)',
                                 'Building structure','Layout','Building age(years)','Renovation']]
            for i in ['Maximum Building Coverage Ratio(%)','Maximum Floor-area Ratio(%)']:
                ref_data_2[i]=ref_data_2[i].astype(int)
            ref_data_1=ref_data_1.style.apply(lambda x: ['background: orange' if v >2018 else '' for v in x], axis = 1,subset=['Sales_transaction_year']).apply(lambda x: ['background: red' if v ==Municipality else '' for v in x], axis = 1,subset=['Municipality']).apply(lambda x: ['background: red' if v ==District else '' for v in x], axis = 1,subset=['District']).apply(lambda x: ['background: red' if v ==Station else '' for v in x], axis = 1,subset=['Nearest_Station']).apply(lambda x: ['background: red' if abs(v-Distance_station)<2 else '' for v in x], axis = 1,subset=['Distance to nearest station (mn)']).apply(lambda x: ['background: orange' if abs(v-Distance_station)>1 and abs(v-Distance_station)<6 else '' for v in x], axis = 1,subset=['Distance to nearest station (mn)']).apply(lambda x: ['background: red' if abs(v-Area[0])<6 else '' for v in x], axis = 1,subset=['Property area(m2)']).apply(lambda x: ['background: orange' if abs(v-Area[0])>5 and abs(v-Area[0])<21  else '' for v in x], axis = 1,subset=['Property area(m2)']).set_properties(**{'text-align': 'center'}).set_properties(**{'text-align': 'center'}).hide_index().set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
            ref_data_2=ref_data_2.apply(lambda x: ['background: red' if abs(v-Building_ratio)<6 else '' for v in x], axis = 1,subset=['Maximum Building Coverage Ratio(%)']).apply(lambda x: ['background: orange' if abs(v-Building_ratio)>5 and abs(v-Building_ratio)<21  else '' for v in x], axis = 1,subset=['Maximum Building Coverage Ratio(%)']).apply(lambda x: ['background: red' if abs(v-Floor_ratio)<6 else '' for v in x], axis = 1,subset=['Maximum Floor-area Ratio(%)']).apply(lambda x: ['background: orange' if abs(v-Floor_ratio)>5 and abs(v-Floor_ratio)<21  else '' for v in x], axis = 1,subset=['Maximum Floor-area Ratio(%)']).apply(lambda x: ['background: red' if v ==Structure else '' for v in x], axis = 1,subset=['Building structure']).apply(lambda x: ['background: red' if abs(v-Building_age)<2 else '' for v in x], axis = 1,subset=['Building age(years)']).apply(lambda x: ['background: orange' if abs(v-Building_age)>1 and abs(v-Building_age)<6 else '' for v in x], axis = 1,subset=['Building age(years)']).apply(lambda x: ['background: red' if v==Layout else '' for v in x], axis = 1,subset=['Layout']).apply(lambda x: ['background: red' if v==Renovation else '' for v in x], axis = 1,subset=['Renovation']).set_properties(**{'text-align': 'center'}).set_properties(**{'text-align': 'center'}).hide_index().set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
        
        Ref_1_html=ref_data_1.render()
        Ref_2_html=ref_data_2.render()
        
        #Explore model
        if User_type=='Buyer':
            Evaluation_Summary=pd.DataFrame()
            Topic=[]
            Score=[]
            Sign=[]

            Reg_max=[]
            Reg_min=[]
            Cat_max=[]

            #####Get the pred result########
            #Distance nearest station   
            Distance_Station_frame=Column_frame.copy()                               
            Base=Distance_Station_frame['Distance_Nearest_Station(mn)'][0]
            if Base<10:
                Min_change=Base
                Max_change=Base
            else:
                Min_change=10
                Max_change=10
            Prediction=[]
            Value=[]
            for i in range(Base-Min_change,Base+Max_change):
                Distance_Station_frame['Distance_Nearest_Station(mn)'][0]=i
                X=np.array(Distance_Station_frame)
                Pred=Model.predict(X)
                Prediction.append(np.exp(Pred)[0]*Coefficient)
                Value.append(i)
            Distance_Station_frame_=pd.DataFrame()
            Distance_Station_frame_['Distance to nearest station (mn)']=Value
            Distance_Station_frame_['Price prediction (JPY)']=Prediction   
            for i in range(len(Distance_Station_frame_['Distance to nearest station (mn)'])): 
                if Distance_Station_frame_['Distance to nearest station (mn)'][i]==Base:
                    Base_pred=Distance_Station_frame_['Price prediction (JPY)'][i]
                    break
            Topic.append('Distance to nearest station (mn)')
            Diff=[]
            for i in range(len(Distance_Station_frame_)):
                if Distance_Station_frame_['Distance to nearest station (mn)'][i]==Base:
                    Diff.append(0)
                else:
                    Diff.append(Distance_Station_frame_['Price prediction (JPY)'][i]-Base_pred)
            Distance_Station_frame_['Diff']=Diff
            Score.append(abs(Distance_Station_frame_['Diff']).max())
            if Distance_Station_frame_['Price prediction (JPY)'][0]>Distance_Station_frame_['Price prediction (JPY)'].iloc[-1]:
                Sign.append('-')
            else:
                Sign.append('+')
            Reg_max.append(np.max(Prediction))
            Reg_min.append(np.min(Prediction))

            #Area
            Area_frame=Column_frame.copy()                                           
            Base=Area_frame['Area(m^2)'][0]
            Base_exp=int(round(np.exp(Area_frame['Area(m^2)'][0]),0))
            Min_change=int(round(Base_exp*0.2,0))
            Max_change=int(round(Base_exp*0.2,0))
            Prediction=[]
            Value=[]
            for i in range(Base_exp-Min_change,Base_exp+Max_change+1):
                Area_frame['Area(m^2)'][0]=np.log(i)
                X=np.array(Area_frame)
                Pred=Model.predict(X)
                Prediction.append(np.exp(Pred)[0]*Coefficient)
                Value.append(i)
            Area_frame_=pd.DataFrame()
            Area_frame_['Property area(m2)']=Value
            Area_frame_['Price prediction (JPY)']=Prediction         
            for i in range(len(Area_frame_['Property area(m2)'])): 
                if Area_frame_['Property area(m2)'][i]==Base:
                    Base_pred=Area_frame_['Price prediction (JPY)'][i]
                    break
            Topic.append('Property area(m2)')
            Diff=[]
            for i in range(len(Area_frame_)):
                if Area_frame_['Property area(m2)'][i]==Base:
                    Diff.append(0)
                else:
                    Diff.append(Area_frame_['Price prediction (JPY)'][i]-Base_pred)
            Area_frame_['Diff']=Diff
            Score.append(abs(Area_frame_['Diff']).max())
            if Area_frame_['Price prediction (JPY)'][0]>Area_frame_['Price prediction (JPY)'].iloc[-1]:
                Sign.append('-')
            else:
                Sign.append('+')
            Reg_max.append(np.max(Prediction))
            Reg_min.append(np.min(Prediction))

             #Building ratio
            Building_Ratio_frame=Column_frame.copy()                                           
            Base=int(round(Building_Ratio_frame['Maximus Building Coverage Ratio(%)'][0],0))
            Min_change=int(Base*0.2)
            Max_change=int(Base*0.2)
            Prediction=[]
            Value=[]
            for i in range(Base-Min_change,Base+Max_change+1):
                Building_Ratio_frame['Maximus Building Coverage Ratio(%)'][0]=i
                X=np.array(Building_Ratio_frame)
                Pred=Model.predict(X)
                Prediction.append(np.exp(Pred)[0]*Coefficient)
                Value.append(i)
            Building_Ratio_frame_=pd.DataFrame()
            Building_Ratio_frame_['Maximum Building Coverage Ratio(%)']=Value
            Building_Ratio_frame_['Price prediction (JPY)']=Prediction         
            for i in range(len(Building_Ratio_frame_['Maximum Building Coverage Ratio(%)'])): 
                if Building_Ratio_frame_['Maximum Building Coverage Ratio(%)'][i]==Base:
                    Base_pred=Building_Ratio_frame_['Price prediction (JPY)'][i]
                    break
            Topic.append('Maximum Building Coverage Ratio(%)')
            Diff=[]
            for i in range(len(Building_Ratio_frame_)):
                if Building_Ratio_frame_['Maximum Building Coverage Ratio(%)'][i]==Base:
                    Diff.append(0)
                else:
                    Diff.append(Building_Ratio_frame_['Price prediction (JPY)'][i]-Base_pred)
            Building_Ratio_frame_['Diff']=Diff
            Score.append(abs(Building_Ratio_frame_['Diff']).max())
            if Building_Ratio_frame_['Price prediction (JPY)'][0]>Building_Ratio_frame_['Price prediction (JPY)'].iloc[-1]:
                Sign.append('-')
            else:
                Sign.append('+')
            Reg_max.append(np.max(Prediction))
            Reg_min.append(np.min(Prediction))

            #Building floor ratio
            Floor_Ratio_frame=Column_frame.copy()                                           
            Base=int(round(Floor_Ratio_frame['Maximus Floor-area Ratio(%)'][0],0))
            Min_change=int(Base*0.2)
            Max_change=int(Base*0.2)
            Prediction=[]
            Value=[]
            for i in range(Base-Min_change,Base+Max_change+1):
                Floor_Ratio_frame['Maximus Floor-area Ratio(%)'][0]=i
                X=np.array(Floor_Ratio_frame)
                Pred=Model.predict(X)
                Prediction.append(np.exp(Pred)[0]*Coefficient)
                Value.append(i)
            Floor_Ratio_frame_=pd.DataFrame()
            Floor_Ratio_frame_['Maximum Floor-area Ratio(%)']=Value
            Floor_Ratio_frame_['Price prediction (JPY)']=Prediction         
            for i in range(len(Floor_Ratio_frame_['Maximum Floor-area Ratio(%)'])): 
                if Floor_Ratio_frame_['Maximum Floor-area Ratio(%)'][i]==Base:
                    Base_pred=Floor_Ratio_frame_['Price prediction (JPY)'][i]
                    break
            Topic.append('Maximum Floor-area Ratio(%)')
            Diff=[]
            for i in range(len(Floor_Ratio_frame_)):
                if Floor_Ratio_frame_['Maximum Floor-area Ratio(%)'][i]==Base:
                    Diff.append(0)
                else:
                    Diff.append(Floor_Ratio_frame_['Price prediction (JPY)'][i]-Base_pred)
            Floor_Ratio_frame_['Diff']=Diff
            Score.append(abs(Floor_Ratio_frame_['Diff']).max())
            if Floor_Ratio_frame_['Price prediction (JPY)'][0]>Floor_Ratio_frame_['Price prediction (JPY)'].iloc[-1]:
                Sign.append('-')
            else:
                Sign.append('+')
            Reg_max.append(np.max(Prediction))
            Reg_min.append(np.min(Prediction))

              #Building_age
            Building_Age_frame=Column_frame.copy()                                           
            Base=int(round(Building_Age_frame['Building_Age'][0],0))
            if Base<5:
                Min_change=Base
            else:
                Min_change=5
            Max_change=5
            Prediction=[]
            Value=[]
            for i in range(Base-Min_change,Base+Max_change+1):
                Building_Age_frame['Building_Age'][0]=i
                X=np.array(Building_Age_frame)
                Pred=Model.predict(X)
                Prediction.append(np.exp(Pred)[0]*Coefficient)
                Value.append(i)
            Building_Age_frame_=pd.DataFrame()
            Building_Age_frame_['Building age(years)']=Value
            Building_Age_frame_['Price prediction (JPY)']=Prediction         
            for i in range(len(Building_Age_frame_['Building age(years)'])): 
                if Building_Age_frame_['Building age(years)'][i]==Base:
                    Base_pred=Building_Age_frame_['Price prediction (JPY)'][i]
                    break
            Topic.append('Building age(years)')
            Diff=[]
            for i in range(len(Building_Age_frame_)):
                if Building_Age_frame_['Building age(years)'][i]=='Base':
                    Diff.append(0)
                else:
                    Diff.append(Building_Age_frame_['Price prediction (JPY)'][i]-Base_pred)
            Building_Age_frame_['Diff']=Diff
            Score.append(abs(Building_Age_frame_['Diff']).max())
            if Building_Age_frame_['Price prediction (JPY)'][0]>Building_Age_frame_['Price prediction (JPY)'].iloc[-1]:
                Sign.append('-')
            else:
                Sign.append('+')
            Reg_max.append(np.max(Prediction))
            Reg_min.append(np.min(Prediction))

            if Type=='House':
                #Total floor area
                Total_Floor_frame=Column_frame.copy()                                           
                Base=Total_Floor_frame['Total floor area(m^2)'][0]
                Base_exp=int(round(np.exp(Base),0))
                Min_change=int(round(Base_exp*0.2,0))
                Max_change=int(round(Base_exp*0.2,0))
                Prediction=[]
                Value=[]
                for i in range(Base_exp-Min_change,Base_exp+Max_change+1):
                    Total_Floor_frame['Total floor area(m^2)'][0]=np.log(i)
                    X=np.array(Total_Floor_frame)
                    Pred=Model.predict(X)
                    Prediction.append(np.exp(Pred)[0]*Coefficient)
                    Value.append(i)
                Total_Floor_frame_=pd.DataFrame()
                Total_Floor_frame_['Total floor area(m^2)']=Value
                Total_Floor_frame_['Price prediction (JPY)']=Prediction         
                for i in range(len(Total_Floor_frame_['Total floor area(m^2)'])): 
                    if Total_Floor_frame_['Total floor area(m^2)'][i]==Base:
                        Base_pred=Total_Floor_frame_['Price prediction (JPY)'][i]
                        break
                Topic.append('Total floor area(m2)')
                Diff=[]
                for i in range(len(Total_Floor_frame_)):
                    if Total_Floor_frame_['Total floor area(m^2)'][i]==Base:
                        Diff.append(0)
                    else:
                        Diff.append(Total_Floor_frame_['Price prediction (JPY)'][i]-Base_pred)
                Total_Floor_frame_['Diff']=Diff
                Score.append(abs(Total_Floor_frame_['Diff']).max())
                if Total_Floor_frame_['Price prediction (JPY)'][0]>Total_Floor_frame_['Price prediction (JPY)'].iloc[-1]:
                    Sign.append('-')
                else:
                    Sign.append('+')
                Reg_max.append(np.max(Prediction))
                Reg_min.append(np.min(Prediction))

            #Frontage road breadth
                Frontage_Breadth_frame=Column_frame.copy()                                           
                Base=Frontage_Breadth_frame['Frontage_Road_Breadth(m)'][0]
                Base_exp=int(round(np.exp(Base),0))
                Min_change=int(round(Base_exp*0.2,0))
                Max_change=int(round(Base_exp*0.2,0))
                Prediction=[]
                Value=[]
                for i in range(Base_exp-Min_change,Base_exp+Max_change+1):
                    Frontage_Breadth_frame['Frontage_Road_Breadth(m)'][0]=np.log(i)
                    X=np.array(Frontage_Breadth_frame)
                    Pred=Model.predict(X)
                    Prediction.append(np.exp(Pred)[0]*Coefficient)
                    Value.append(i)
                Frontage_Breadth_frame_=pd.DataFrame()
                Frontage_Breadth_frame_['Frontage road breadth(m)']=Value
                Frontage_Breadth_frame_['Price prediction (JPY)']=Prediction 
                for i in range(len(Frontage_Breadth_frame_['Frontage road breadth(m)'])): 
                    if Frontage_Breadth_frame_['Frontage road breadth(m)'][i]==Base:
                        Base_pred=Frontage_Breadth_frame_['Price prediction (JPY)'][i]
                        break
                Topic.append('Frontage road breadth(m)')
                Diff=[]
                for i in range(len(Frontage_Breadth_frame_)):
                    if Frontage_Breadth_frame_['Frontage road breadth(m)'][i]==Base:
                        Diff.append(0)
                    else:
                        Diff.append(Frontage_Breadth_frame_['Price prediction (JPY)'][i]-Base_pred)
                Frontage_Breadth_frame_['Diff']=Diff
                Score.append(abs(Frontage_Breadth_frame_['Diff']).max())
                if Frontage_Breadth_frame_['Price prediction (JPY)'][0]>Frontage_Breadth_frame_['Price prediction (JPY)'].iloc[-1]:
                    Sign.append('-')
                else:
                    Sign.append('+')
                Reg_max.append(np.max(Prediction))
                Reg_min.append(np.min(Prediction))

                #Frontage Road direction
                Frontage_Direction_frame=Column_frame.copy()  
                Base=None
                for i in ['Frontage_Road_Direction_South','Frontage_Road_Direction_North','Frontage_Road_Direction_East',
                          'Frontage_Road_Direction_West','Frontage_Road_Direction_Southwest','Frontage_Road_Direction_Southeast',
                          'Frontage_Road_Direction_Northwest','Frontage_Road_Direction_Northeast']:
                    if i in Frontage_Direction_frame.columns:
                        if Frontage_Direction_frame[i][0]==1:
                            substring=i.split('Frontage_Road_Direction_',1)
                            Base=substring[1]
                            break
                if Base==None:
                    Base='Unknown'
                Prediction=[]
                Value=[]
                for i in ['Frontage_Road_Direction_South','Frontage_Road_Direction_North','Frontage_Road_Direction_East','Frontage_Road_Direction_West','Frontage_Road_Direction_Southwest','Frontage_Road_Direction_Southeast','Frontage_Road_Direction_Northwest','Frontage_Road_Direction_Northeast']:
                    for k in ['Frontage_Road_Direction_South','Frontage_Road_Direction_North','Frontage_Road_Direction_East',
                          'Frontage_Road_Direction_West','Frontage_Road_Direction_Southwest','Frontage_Road_Direction_Southeast',
                          'Frontage_Road_Direction_Northwest','Frontage_Road_Direction_Northeast']:
                        if k in Frontage_Direction_frame.columns:
                            Frontage_Direction_frame[k]=[0]
                    if i in Frontage_Direction_frame.columns:
                        Frontage_Direction_frame[i]=[1]
                        X=np.array(Frontage_Direction_frame)
                        Pred=Model.predict(X)
                        Prediction.append(np.exp(Pred)[0]*Coefficient)
                        substring=i.split('Frontage_Road_Direction_',1)
                        title=substring[1]
                        if title=='South':
                            title='S'
                        elif title=='North':
                            title='N'
                        elif title=='West':
                            title='W'
                        elif title=='East':
                            title='E'
                        elif title=='Southwest':
                            title='SW'
                        elif title=='Southeast':
                            title='SE'
                        elif title=='Northwest':
                            title='NW'
                        else:
                            title='NE'
                        Value.append(title)
                if Base=='Unknown':
                    for k in ['Frontage_Road_Direction_South','Frontage_Road_Direction_North','Frontage_Road_Direction_East','Frontage_Road_Direction_West','Frontage_Road_Direction_Southwest','Frontage_Road_Direction_Southeast','Frontage_Road_Direction_Northwest','Frontage_Road_Direction_Northeast']:
                        if k in Frontage_Direction_frame.columns:
                            Frontage_Direction_frame[k]=[0]
                    X=np.array(Frontage_Direction_frame)
                    Pred=Model.predict(X)
                    Prediction.append(np.exp(Pred)[0]*Coefficient)
                    Value.append('Unknown')
                Frontage_Direction_frame_=pd.DataFrame()
                Frontage_Direction_frame_['Frontage road direction']=Value
                Frontage_Direction_frame_['Price prediction (JPY)']=Prediction      
                for i in range(len(Frontage_Direction_frame_['Frontage road direction'])): 
                    if Frontage_Direction_frame_['Frontage road direction'][i]==Base:
                        Base_pred=Frontage_Direction_frame_['Price prediction (JPY)'][i]
                        break
                Topic.append('Frontage road direction')
                Diff=[]
                for i in range(len(Frontage_Direction_frame_)):
                    if Frontage_Direction_frame_['Frontage road direction'][i]==Base:
                        Diff.append(0)
                    else:
                        Diff.append(Frontage_Direction_frame_['Price prediction (JPY)'][i]-Base_pred)
                Frontage_Direction_frame_['Diff']=Diff
                Score.append(abs(Frontage_Direction_frame_['Diff']).max())
                if Frontage_Direction_frame_['Diff'].max()<abs(Frontage_Direction_frame_['Diff'].min()):
                    Sign.append('-')
                else:
                    Sign.append('+')
                Cat_max.append(np.max(Prediction))

            #Building structure
            Building_Structure_frame=Column_frame.copy() 
            Base=None
            for i in ['Building_structure_RC','Building_structure_SRC','Building_structure_S','Building_structure_B','Building_structure_W','Building_structure_LS']:
                 if Building_Structure_frame[i][0]==1:
                    substring=i.split('Building_structure_',1)
                    Base=substring[1]
                    break
            if Base==None:
                Base='Unknown'
            Prediction=[]
            Value=[]
            for i in ['Building_structure_RC','Building_structure_SRC','Building_structure_S','Building_structure_B','Building_structure_W','Building_structure_LS']:
                for k in ['Building_structure_RC','Building_structure_SRC','Building_structure_S','Building_structure_B','Building_structure_W','Building_structure_LS']:
                    Building_Structure_frame[k]=[0]
                Building_Structure_frame[i]=[1]
                X=np.array(Building_Structure_frame)
                Pred=Model.predict(X)
                Prediction.append(np.exp(Pred)[0]*Coefficient)
                substring=i.split('Building_structure_',1)
                title=substring[1]
                Value.append(title)
            if Base=='Unknown':
                for k in ['Building_structure_RC','Building_structure_SRC','Building_structure_S','Building_structure_B','Building_structure_W','Building_structure_LS']:
                    Building_Structure_frame[k]=[0]
                X=np.array(Building_Structure_frame)
                Pred=Model.predict(X)
                Prediction.append(np.exp(Pred)[0]*Coefficient)
                Value.append('Unknown')

            Building_Structure_frame_=pd.DataFrame()
            Building_Structure_frame_['Building structure']=Value
            Building_Structure_frame_['Price prediction (JPY)']=Prediction      
            for i in range(len(Building_Structure_frame_['Building structure'])): 
                if Building_Structure_frame_['Building structure'][i]==Base:
                    Base_pred=Building_Structure_frame_['Price prediction (JPY)'][i]
                    break
            Topic.append('Building structure')
            Diff=[]
            for i in range(len(Building_Structure_frame_)):
                if Building_Structure_frame_['Building structure'][i]==Base:
                    Diff.append(0)
                else:
                    Diff.append(Building_Structure_frame_['Price prediction (JPY)'][i]-Base_pred)
            Building_Structure_frame_['Diff']=Diff
            Score.append(abs(Building_Structure_frame_['Diff']).max())
            if Building_Structure_frame_['Diff'].max()<abs(Building_Structure_frame_['Diff'].min()):
                Sign.append('-')
            else:
                Sign.append('+')
            Cat_max.append(np.max(Prediction))

            #District
            District_frame=Column_frame.copy()
            Base=District
            Translation=pd.read_csv('Translation_file.csv',encoding='cp932')
            Translation=Translation[Translation['Municipality_Eng']==Municipality].reset_index(drop=True)
            Translation=Translation.drop_duplicates(subset=['District_Eng']).reset_index(drop=True)
            District_list=[]
            for i in Translation['District_Eng']:
                District_list.append('District_'+i)
            Value=[]
            Prediction=[]
            for i in District_list:
                for k in District_list:
                    if k in District_frame.columns:
                        District_frame[k]=[0]
                if i in District_frame.columns:
                    District_frame[i]=[1]
                    X=np.array(District_frame)
                    Pred=Model.predict(X)
                    Prediction.append(np.exp(Pred)[0]*Coefficient)
                    substring=i.split('District_',1)
                    title=substring[1]
                    Value.append(title)
            District_frame_=pd.DataFrame()
            District_frame_['District']=Value
            District_frame_['Price prediction (JPY)']=Prediction      
            for i in range(len(District_frame_['District'])): 
                if District_frame_['District'][i][0]==Base:
                    Base_pred=District_frame_['Price prediction (JPY)'][i]
                    break
            Topic.append('District')
            Diff=[]
            for i in range(len(District_frame_)):
                if District_frame_['District'][i]==Base:
                    Diff.append(0)
                else:
                    Diff.append(District_frame_['Price prediction (JPY)'][i]-Base_pred)
            District_frame_['Diff']=Diff
            Score.append(abs(District_frame_['Diff']).max())
            if District_frame_['Diff'].max()<abs(District_frame_['Diff'].min()):
                Sign.append('-')
            else:
                Sign.append('+')
            Cat_max.append(np.max(Prediction))

            if len(District_frame_)>8:
                District_frame_=District_frame_.sort_values(by='Price prediction (JPY)').reset_index(drop=True)
                Check=[]
                for i in range(len(District_frame_)):
                    if i<4 or i>len(District_frame_)-4 or District_frame_['District'][i]==Base:
                        Check.append(1)
                    else:
                        Check.append(0)
                District_frame_['Check']=Check
                District_frame_=District_frame_[District_frame_['Check']==1].reset_index(drop=True)     


            if Type=='Mansion':
                #Layout
                Layout_frame=Column_frame.copy() 
                Base=None
                for i in ['Layout_1K','Layout_2K','Layout_3K','Layout_4K','Layout_5K','Layout_1DK','Layout_2DK',
                          'Layout_3DK','Layout_4DK','Layout_5DK','Layout_6DK','Layout_7DK','Layout_1LDK','Layout_2LDK',
                          'Layout_3LDK','Layout_4LDK','Layout_5LDK','Layout_6LDK','Layout_7LDK','Layout_8LDK','Layout_1R']:
                    if i in Layout_frame.columns:
                        if Layout_frame[i][0]==1:
                            substring=i.split('Layout_',1)
                            Base=substring[1]
                            break
                if Base==None:
                    Base='Unknown'
                Prediction=[]
                Value=[]

                for i in ['Layout_1K','Layout_2K','Layout_3K','Layout_4K','Layout_5K','Layout_1DK','Layout_2DK',
                          'Layout_3DK','Layout_4DK','Layout_5DK','Layout_6DK','Layout_7DK','Layout_1LDK','Layout_2LDK',
                          'Layout_3LDK','Layout_4LDK','Layout_5LDK','Layout_6LDK','Layout_7LDK','Layout_8LDK','Layout_1R']:
                    for k in ['Layout_1K','Layout_2K','Layout_3K','Layout_4K','Layout_5K','Layout_1DK','Layout_2DK',
                          'Layout_3DK','Layout_4DK','Layout_5DK','Layout_6DK','Layout_7DK','Layout_1LDK','Layout_2LDK',
                          'Layout_3LDK','Layout_4LDK','Layout_5LDK','Layout_6LDK','Layout_7LDK','Layout_8LDK','Layout_1R']:
                        if k in Layout_frame.columns:
                            Layout_frame[k]=[0]
                    if i in Layout_frame.columns:
                        Layout_frame[i]=[1]
                        X=np.array(Layout_frame)
                        Pred=Model.predict(X)
                        Prediction.append(np.exp(Pred)[0]*Coefficient)
                        substring=i.split('Layout_',1)
                        title=substring[1]
                        Value.append(title)
                if Base=='Unknown':
                    for k in ['Layout_1K','Layout_2K','Layout_3K','Layout_4K','Layout_5K','Layout_1DK','Layout_2DK',
                          'Layout_3DK','Layout_4DK','Layout_5DK','Layout_6DK','Layout_7DK','Layout_1LDK','Layout_2LDK',
                          'Layout_3LDK','Layout_4LDK','Layout_5LDK','Layout_6LDK','Layout_7LDK','Layout_8LDK','Layout_1R']:
                        if k in Layout_frame.columns:
                            Layout_frame[k]=[0]
                    X=np.array(Layout_frame)
                    Pred=Model.predict(X)
                    Prediction.append(np.exp(Pred)[0]*Coefficient)
                    Value.append('Unknonwn')

                Layout_frame_=pd.DataFrame()
                Layout_frame_['Layout']=Value
                Layout_frame_['Price prediction (JPY)']=Prediction      
                for i in range(len(Layout_frame_['Layout'])): 
                    if Layout_frame_['Layout'][i][0]==Base:
                        Base_pred=Layout_frame_['Price prediction (JPY)'][i]
                        break
                Topic.append('Layout')
                Diff=[]
                for i in range(len(Layout_frame_)):
                    if Layout_frame_['Layout'][i]==Base:
                        Diff.append(0)
                    else:
                        Diff.append(Layout_frame_['Price prediction (JPY)'][i]-Base_pred)
                Layout_frame_['Diff']=Diff
                Score.append(abs(Layout_frame_['Diff']).max())
                if Layout_frame_['Diff'].max()<abs(Layout_frame_['Diff'].min()):
                    Sign.append('-')
                else:
                    Sign.append('+')
                Cat_max.append(np.max(Prediction))

                if len(Layout_frame_)>8:
                    Layout_frame_=Layout_frame_.sort_values(by='Price prediction (JPY)').reset_index(drop=True)
                    Check=[]
                    for i in range(len(Layout_frame_)):
                        if i<4 or i>len(Layout_frame_)-4 or Layout_frame_['Layout'][i]==Base:
                            Check.append(1)
                        else:
                            Check.append(0)
                    Layout_frame_['Check']=Check
                    Layout_frame_=Layout_frame_[Layout_frame_['Check']==1].reset_index(drop=True)


                #Renovation
                Renovation_frame=Column_frame.copy()  
                for i in ['Not Yet','Done','Unknown']:
                    if i in Renovation_frame.columns:
                        if Renovation_frame['Renovation_'+str(i)][0]==1:
                            substring=i.split('Renovation_',1)
                            Base=substring[1]
                            break
                Prediction=[]
                Value=[]                
                for i in ['Renovation_Not yet','Renovation_Done','Renovation_Unknown']:
                    for k in ['Renovation_Not yet','Renovation_Done','Renovation_Unknown']:
                        if k in Renovation_frame.columns:
                            Renovation_frame[k]=[0]
                    if i in Renovation_frame.columns:
                        Renovation_frame[i]=[1]
                        X=np.array(Renovation_frame)
                        Pred=Model.predict(X)
                        Prediction.append(np.exp(Pred)[0]*Coefficient)
                        substring=i.split('Renovation_',1)
                        title=substring[1]
                        Value.append(title)
                Renovation_frame_=pd.DataFrame()
                Renovation_frame_['Renovation']=Value
                Renovation_frame_['Price prediction (JPY)']=Prediction      
                for i in range(len(Renovation_frame_['Renovation'])): 
                    if Renovation_frame_['Renovation'][i]==Base:
                        Base_pred=Renovation_frame_['Price prediction (JPY)'][i]
                        break
                Topic.append('Renovation')
                Diff=[]
                for i in range(len(Renovation_frame_)):
                    if Renovation_frame_['Renovation'][i]==Base:
                        Diff.append(0)
                    else:
                        Diff.append(Renovation_frame_['Price prediction (JPY)'][i]-Base_pred)
                Renovation_frame_['Diff']=Diff
                Score.append(abs(Renovation_frame_['Diff']).max())
                if Renovation_frame_['Diff'].max()<abs(Renovation_frame_['Diff'].min()):
                    Sign.append('-')
                else:
                    Sign.append('+')
                Cat_max.append(np.max(Prediction))


            ######Make the graphs with scale######
            Reg_max=np.max(Reg_max)
            Reg_min=np.min(Reg_min)
            Pos_Y=(Final_pred-Reg_min)/(Reg_max-Reg_min)
            Cat_max=np.max(Cat_max)

            #Distance nearest station  
            plt.figure()
            Distance_Station_plot=sns.lineplot(data=Distance_Station_frame_, x='Distance to nearest station (mn)', y='Price prediction (JPY)')
            plt.title("Distance to nearest station effect on price prediction",fontsize=12)
            Distance_Station_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))    
            Max_y_x=Distance_Station_frame_['Price prediction (JPY)'].max()
            Min_y_x=Distance_Station_frame_['Price prediction (JPY)'].min()
            if Distance_Station_frame_['Price prediction (JPY)'][0]<list(Distance_Station_frame_['Price prediction (JPY)'])[-1]:
                Pos_X=(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            else:
                Pos_X=1-(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            Distance_Station_plot.annotate('X',xy=(Pos_X, Pos_Y), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
            Distance_Station_plot.annotate('(Current position)',xy=(Pos_X, Pos_Y-0.05), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=10,color='red')
            Distance_Station_plot.set(ylim=(Reg_min-Reg_max*0.02,Reg_max+Reg_max*0.02))
            encoded = fig_to_base64(Distance_Station_plot)
            Distance_Station_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

            #Area
            plt.figure()
            Area_plot=sns.lineplot(data=Area_frame_, x='Property area(m2)', y='Price prediction (JPY)')
            plt.title('Property area(m2) effect on price prediction',fontsize=12)
            Area_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            Max_y_x=Area_frame_['Price prediction (JPY)'].max()
            Min_y_x=Area_frame_['Price prediction (JPY)'].min()
            if Area_frame_['Price prediction (JPY)'][0]<list(Area_frame_['Price prediction (JPY)'])[-1]:
                Pos_X=(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            else:
                Pos_X=1-(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            Area_plot.annotate('X',xy=(Pos_X, Pos_Y), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
            Area_plot.annotate('(Current position)',xy=(Pos_X, Pos_Y-0.05), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=10,color='red')
            Area_plot.set(ylim=(Reg_min-Reg_max*0.02,Reg_max+Reg_max*0.02))
            encoded = fig_to_base64(Area_plot)
            Area_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

                #Building ratio
            plt.figure()
            Building_ratio_plot=sns.lineplot(data=Building_Ratio_frame_, x='Maximum Building Coverage Ratio(%)', y='Price prediction (JPY)')
            plt.title('Maximum Building Coverage Ratio(%) effect on price prediction',fontsize=12)
            Building_ratio_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            Max_y_x=Building_Ratio_frame_['Price prediction (JPY)'].max()
            Min_y_x=Building_Ratio_frame_['Price prediction (JPY)'].min()
            if Building_Ratio_frame_['Price prediction (JPY)'][0]<list(Building_Ratio_frame_['Price prediction (JPY)'])[-1]:
                Pos_X=(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            else:
                Pos_X=1-(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            Building_ratio_plot.annotate('X',xy=(Pos_X, Pos_Y), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
            Building_ratio_plot.annotate('(Current position)',xy=(Pos_X, Pos_Y-0.05), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=10,color='red')
            Building_ratio_plot.set(ylim=(Reg_min-Reg_max*0.02,Reg_max+Reg_max*0.02))
            encoded = fig_to_base64(Building_ratio_plot)
            Building_ratio_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

                    #Floor ratio
            plt.figure()
            Floor_ratio_plot=sns.lineplot(data=Floor_Ratio_frame_, x='Maximum Floor-area Ratio(%)', y='Price prediction (JPY)')
            plt.title('Maximum Floor-area Ratio(%) effect on price prediction',fontsize=12)
            Floor_ratio_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            Max_y_x=Floor_Ratio_frame_['Price prediction (JPY)'].max()
            Min_y_x=Floor_Ratio_frame_['Price prediction (JPY)'].min()
            if Floor_Ratio_frame_['Price prediction (JPY)'][0]<list(Floor_Ratio_frame_['Price prediction (JPY)'])[-1]:
                Pos_X=(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            else:
                Pos_X=1-(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            Floor_ratio_plot.annotate('X',xy=(Pos_X, Pos_Y), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
            Floor_ratio_plot.annotate('(Current position)',xy=(Pos_X, Pos_Y-0.05), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=10,color='red')
            Floor_ratio_plot.set(ylim=(Reg_min-Reg_max*0.02,Reg_max+Reg_max*0.02))
            encoded = fig_to_base64(Floor_ratio_plot)
            Floor_ratio_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

                        #Building_age
            plt.figure()
            Building_age_plot=sns.lineplot(data=Building_Age_frame_, x='Building age(years)', y='Price prediction (JPY)')
            plt.title('Building age(years) effect on price prediction',fontsize=12)
            Building_age_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            Max_y_x=Building_Age_frame_['Price prediction (JPY)'].max()
            Min_y_x=Building_Age_frame_['Price prediction (JPY)'].min()
            if Building_Age_frame_['Price prediction (JPY)'][0]<list(Building_Age_frame_['Price prediction (JPY)'])[-1]:
                Pos_X=(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            else:
                Pos_X=1-(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
            Building_age_plot.annotate('X',xy=(Pos_X, Pos_Y), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
            Building_age_plot.annotate('(Current position)',xy=(Pos_X, Pos_Y-0.05), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=10,color='red')
            Building_age_plot.set(ylim=(Reg_min-Reg_max*0.02,Reg_max+Reg_max*0.02))
            encoded = fig_to_base64(Building_age_plot)
            Building_age_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

            if Type=='House':
                #Total floor area
                plt.figure()
                Total_floor_area_plot=sns.lineplot(data=Total_Floor_frame_, x='Total floor area(m^2)', y='Price prediction (JPY)')
                plt.title('Total floor area(m^2) effect on price prediction',fontsize=12)
                Total_floor_area_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
                Max_y_x=Total_Floor_frame_['Price prediction (JPY)'].max()
                Min_y_x=Total_Floor_frame_['Price prediction (JPY)'].min()
                if Total_Floor_frame_['Price prediction (JPY)'][0]<list(Total_Floor_frame_['Price prediction (JPY)'])[-1]:
                    Pos_X=(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
                else:
                    Pos_X=1-(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
                Total_floor_area_plot.annotate('X',xy=(Pos_X, Pos_Y), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
                Total_floor_area_plot.annotate('(Current position)',xy=(Pos_X, Pos_Y-0.05), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=10,color='red')
                Total_floor_area_plot.set(ylim=(Reg_min-Reg_max*0.02,Reg_max+Reg_max*0.02))
                encoded = fig_to_base64(Total_floor_area_plot)
                Floor_area_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

                #Frontage road breadth
                plt.figure()
                Frontage_Road_Breadth_plot=sns.lineplot(data=Frontage_Breadth_frame_, x='Frontage road breadth(m)', y='Price prediction (JPY)')
                plt.title('Frontage road breadth(m) effect on price prediction',fontsize=12)
                Frontage_Road_Breadth_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
                Max_y_x=Frontage_Breadth_frame_['Price prediction (JPY)'].max()
                Min_y_x=Frontage_Breadth_frame_['Price prediction (JPY)'].min()
                if Frontage_Breadth_frame_['Price prediction (JPY)'][0]<list(Distance_Station_frame_['Price prediction (JPY)'])[-1]:
                    Pos_X=(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
                else:
                    Pos_X=1-(Final_pred-Min_y_x)/(Max_y_x-Min_y_x)
                Frontage_Road_Breadth_plot.annotate('X',xy=(Pos_X, Pos_Y), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
                Frontage_Road_Breadth_plot.annotate('(Current position)',xy=(Pos_X, Pos_Y-0.05), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=10,color='red')
                Frontage_Road_Breadth_plot.set(ylim=(Reg_min-Reg_max*0.02,Reg_max+Reg_max*0.02))
                encoded = fig_to_base64(Frontage_Road_Breadth_plot)
                Frontage_breadth_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

                #Frontage Road direction
                plt.figure()
                clrs = ['red' if x==Final_pred else 'grey' for x in Frontage_Direction_frame_['Price prediction (JPY)']]
                Frontage_road_direction_plot=sns.barplot(x='Frontage road direction', y='Price prediction (JPY)', data=Frontage_Direction_frame_,palette=clrs)
                plt.title('Frontage road direction effect on price prediction',fontsize=12)
                Frontage_road_direction_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
                Frontage_road_direction_plot.annotate('■',xy=(0.9, 0.95), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
                Frontage_road_direction_plot.annotate('Current position',xy=(0.9, 0.9), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=7,color='red')
                Frontage_road_direction_plot.set(ylim=(0,Cat_max+Cat_max*0.1))
                encoded = fig_to_base64(Frontage_road_direction_plot)
                Frontage_direction_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))
            else:
                Floor_area_html=0
                Frontage_breadth_html=0
                Frontage_direction_html=0

            #Building structure
            plt.figure()
            clrs = ['red' if x==Final_pred else 'grey' for x in Building_Structure_frame_['Price prediction (JPY)']]
            Building_Structure_plot=sns.barplot(x='Building structure', y='Price prediction (JPY)', data=Building_Structure_frame_,palette=clrs)
            plt.title('Building structure effect on price prediction',fontsize=12)
            Building_Structure_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            Building_Structure_plot.annotate('■',xy=(0.9, 0.95), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
            Building_Structure_plot.annotate('Current position',xy=(0.9, 0.9), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=7,color='red')
            Building_Structure_plot.set(ylim=(0,Cat_max+Cat_max*0.1))
            encoded = fig_to_base64(Building_Structure_plot)
            Building_structure_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

            #District
            plt.figure(figsize=(8,12))
            clrs = ['red' if x==Final_pred else 'grey' for x in District_frame_['Price prediction (JPY)']]
            District_plot=sns.barplot(x='Price prediction (JPY)',y='District', data=District_frame_,palette=clrs)
            plt.title('District location effect on price prediction',fontsize=12)
            District_plot.get_xaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            District_plot.xaxis.set_major_locator(plt.MaxNLocator(3))
            District_plot.annotate('■',xy=(0.9, 0.93), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=18,color='red')
            District_plot.annotate('Current position',xy=(0.9, 0.9), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=11,color='red')
            District_plot.set(xlim=(0,Cat_max+Cat_max*0.1))
            encoded = fig_to_base64(District_plot)
            District_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

            if Type=='Mansion':
                #Layout
                plt.figure()
                clrs = ['red' if x==Final_pred else 'grey' for x in Layout_frame_['Price prediction (JPY)']]
                Layout_plot=sns.barplot(x='Layout', y='Price prediction (JPY)', data=Layout_frame_,palette=clrs)
                plt.title('Layout effect on price prediction',fontsize=12)
                Layout_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
                Layout_plot.annotate('■',xy=(0.9, 0.95), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
                Layout_plot.annotate('Current position',xy=(0.9, 0.9), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=7,color='red')
                Layout_plot.set(ylim=(0,Cat_max+Cat_max*0.1))
                encoded = fig_to_base64(Layout_plot)
                Layout_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))

                #Renovation
                plt.figure()
                clrs = ['red' if x==Final_pred else 'grey' for x in Renovation_frame_['Price prediction (JPY)']]
                Renovation_plot=sns.barplot(x='Renovation', y='Price prediction (JPY)', data=Renovation_frame_,palette=clrs)
                plt.title('Renovation effect on price prediction',fontsize=12)
                Renovation_plot.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
                Renovation_plot.annotate('■',xy=(0.9, 0.95), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=14,color='red')
                Renovation_plot.annotate('Current position',xy=(0.9, 0.9), xycoords='axes fraction',horizontalalignment='center', verticalalignment='center',fontsize=7,color='red')
                Renovation_plot.set(ylim=(0,Cat_max+Cat_max*0.1))
                encoded = fig_to_base64(Renovation_plot)
                Renovation_html = 'data:image/png;base64,{}'.format(encoded.decode('utf-8'))
            else:
                Layout_html=0
                Renovation_html=0

            Evaluation_Summary['Category']=Topic
            Evaluation_Summary['Score']=Score
            Evaluation_Summary['Price_variation']=Sign
            Evaluation_Summary=Evaluation_Summary.sort_values(by='Score', ascending=False).reset_index(drop=True)
            Evaluation_Summary['Impact on price rank']=Evaluation_Summary.index.array+1
            Evaluation_Summary=Evaluation_Summary[['Impact on price rank','Category','Price_variation']] 
        else:
            Distance_Station_html=0
            Area_html=0
            Building_ratio_html=0
            Floor_ratio_html=0
            Building_age_html=0
            Floor_area_html=0
            Frontage_breadth_html=0
            Frontage_direction_html=0
            Building_structure_html=0
            District_html=0
            Layout_html=0
            Renovation_html=0
            Evaluation_Summary=0

                                             
    return Prediction_html,Prediction_Warning,Message,Confidence_index,Ref_1_html,Ref_2_html,Distance_Station_html,Area_html,Building_ratio_html,Floor_ratio_html,Building_age_html,Floor_area_html,Frontage_breadth_html,Frontage_direction_html,Building_structure_html,District_html,Layout_html,Renovation_html,Evaluation_Summary,Type
    

#App Home
@application.route('/')
def home_index():
    return render_template('Home.html')

@application.route('/home')
def home():
    return render_template('Home.html')

#App_Buy
@application.route('/Buy_house_prediction',methods=['POST','GET'])
def Buy():
    if request.method=='POST':
        Link=request.form['Sumo_link']
        Output=Get_result(Link,'Buyer','Sumo')
        Prediction_graph=Output[0]
        Prediction_warning=Output[1]
        Message=Output[2]
        Confidence_index=Output[3]
        Hist_data_graph1=Output[4]
        Hist_data_graph2=Output[5]
        Distance_station_graph=Output[6]
        Area_graph=Output[7]
        Building_ratio_graph=Output[8]
        Floor_ratio_graph=Output[9]
        Building_age_graph=Output[10]
        Floor_area_graph=Output[11]
        Frontage_breadth_graph=Output[12]
        Frontage_direction_graph=Output[13]
        Building_structure_graph=Output[14]
        District_graph=Output[15]
        Layout_graph=Output[16]
        Renovation_graph=Output[17]
        Evaluation_Summary=Output[18]
        Type=Output[19]
        Graph_Order=[]
        for i in Evaluation_Summary['Category']:
            if i=='Distance to nearest station (mn)':
                Graph_Order.append(Distance_station_graph)
            elif i=='Property area(m2)':
                Graph_Order.append(Area_graph)
            elif i=='Maximum Building Coverage Ratio(%)':
                Graph_Order.append(Building_ratio_graph)
            elif i=='Maximum Floor-area Ratio(%)':
                Graph_Order.append(Floor_ratio_graph)
            elif i=='Renovation':
                Graph_Order.append(Renovation_graph)
            elif i=='Building age(years)':
                Graph_Order.append(Building_age_graph)
            elif i=='Layout':
                Graph_Order.append(Layout_graph)
            elif i=='District':
                Graph_Order.append(District_graph)
            elif i=='Building structure':
                Graph_Order.append(Building_structure_graph)
            elif i=='Frontage road breath(m)':
                Graph_Order.append(Frontage_breadth_graph)
            elif i=='Frontage road direction':
                Graph_Order.append(Frontage_direction_graph)
            elif i=='Total floor area(m2)':
                Graph_Order.append(Floor_area_graph)            
        Ev_summary_styled=Evaluation_Summary.style.set_properties(**{'text-align': 'center'}).hide_index().set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
        Ev_summary_graph=Ev_summary_styled.render()
        return render_template('Buy_home.html',Pattern=1,Link=Link,Prediction_graph=Prediction_graph,Prediction_warning=Prediction_warning,Message=Message,Confidence_index=Confidence_index,Hist_data_graph1=Hist_data_graph1,Hist_data_graph2=Hist_data_graph2,Ev_summary_graph=Ev_summary_graph,Graphs=Graph_Order)   
    else:
        return render_template('Buy_home.html',Pattern=0)

#App_Sell
@application.route('/Sell_house_prediction')
def Sell():
    return render_template('Sell_home.html')

#App_About
@application.route('/About')
def About():
    return render_template('About.html')

if __name__ == "__main__":
    application.run()
