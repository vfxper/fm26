import pandas as pd
import io

content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
  Messi  ,  AM  ,37,180,180,  Argentina  ,  Club  ,15,14,20,18,20,17,8,16,5,6,19,15,7,20,8,18,12,18,17,18,16,20,15,19,10,16,20,15,16,15,18,10,14,16,14,12,  £50000000  ,50000,170,72,20,15,  messi001  """

df = pd.read_csv(io.StringIO(content), dtype=str)
print(f"Columns: {len(df.columns)}")
print(f"Column names: {df.columns.tolist()}")
print(f"uid value: '{df.iloc[0]['uid']}'")
print(f"price value: '{df.iloc[0]['price']}'")
