import json
import spacy
nlp = spacy.load('en_core_web_lg')

from flask import Flask,request ,Response          
app = Flask(__name__)             

from neo4j import GraphDatabase, basic_auth
# from .utils import *
driver = GraphDatabase.driver(
    "bolt://52.23.213.41:32889", 
    auth=basic_auth("neo4j", "discrepancy-apparatus-operand"))
session = driver.session()

def load_csv(tx,file1,file2):

    for record in tx.run("LOAD CSV WITH HEADERS FROM $file1 AS row "                         
                         "WITH toInteger(row.Index) as index, row.Argument as argument "
                         "MERGE (a:Argument {index: index})"
                         "ON CREATE SET a.Argument = argument",file1=file1
                         ):

        print(record["index"])
    
    for record in tx.run("LOAD CSV WITH HEADERS FROM $file2 AS row "
                         "WITH toInteger(row.attacked) as attackedID , toInteger(row.attacking) as attackingID, toFLoat(row.attack) as attackValue "
                         "MATCH (a:Argument {index: attackedID}) "
                         "MATCH (b: Argument {index: attackingID}) "
                         "MERGE (a)-[r:RATTACK {attackValue: attackValue}]->(b)" 
                         ""
                         "" ,file2=file2
                         ):
        print(record["attackedID"] , record["attackingID"] , record["attackValue"])      

    for record in tx.run("LOAD CSV WITH HEADERS FROM $file2 AS row "
                         "WITH toInteger(row.attacked) as attackedID , toInteger(row.attacking) as attackingID, toFLoat(row.attack) as attackValue "
                         "MATCH (a:Argument {index: attackedID}) "
                         "MATCH (b: Argument {index: attackingID}) "
                         "MERGE (b)-[r:ATTACK {attackValue: attackValue}]->(a)" 
                         ""
                         "" ,file2=file2
                         ):
        print(record["attackedID"] , record["attackingID"] , record["attackValue"])      
   
def delete_all(tx):
    # tx.run("MATCH (a:Argument)-[r:RATTACK]->(b:Argument) DELETE r" )
    # tx.run("MATCH (a:Argument)-[r:ATTACK]->(b:Argument) DELETE r" )  
    # tx.run("MATCH (a:Argument) DELETE a")   
    tx.run("MATCH (n) DETACH DELETE n")

# def find_path(tx, index = 1 , depth , type): # type==1 means deterministic else if type==0 means probabilistic
#     paths = []
    # result =  tx.run("MATCH (a: Argument {index: $index}) "
    #                      "MATCH (b: Argument) "
    #                      "MATCH p = (a)-[:RATTACK *1 ]->(b) "
    #                      "RETURN relationships(p) AS path " , index = index)

#     for record in result:
#         paths.append(record["path"])

#     utility = 0.0
#     maxutil = 0.0

#     # print(paths)
    
#     for path in paths:
#         counter = 0;
#         utility = 0.0
#         # print(path)
#         for r in path:
            
#             # print(r["attackValue"])
#             if(r["attackValue"]==None):
#                 continue

#             if(counter%2==0):
#                 utility= utility + r["attackValue"]
#             else:
#                 utility=  utility- r["attackValue"]
            
            
#             counter+=1
#             # print(counter)
#         if(counter==1):
#             # print("tralala")
#             if(maxutil<utility): 
#                 maxutil = utility
#         # print(maxutil)

#     # print(maxutil)
#     return maxutil
    
def penalty(tx, index,depth):
    print("PENLATY" ,index,depth)
    if depth<=0:
        return 0

    result = tx.run("MATCH (a: Argument {index: $index})"
                    "MATCH (b: Argument)"
                    "MATCH (a)-[r:RATTACK ]->(b)"
                    "RETURN r.attackValue AS attackval, b as attackedNode" , index = index)

    total_penalty = 0
    length =0 
    print(result)
    for record in result:
        print(record)
        attackedNode = record["attackedNode"]
        attackval = record["attackval"]
        # print( "attacked node ", attackedNode)
        # print("attack value " ,  attackval)
        if(attackval==None):
            continue
        length +=1
        
        attackId = attackedNode["index"]
        # print("Attack id: ")
        print(attackId)
        total_penalty +=  attackval - driver.session().read_transaction(penalty,attackId,depth-1)
        # print("util at ", util)
        # if(util > maxutil):
        #     maxutil = util
        #     # print("max at attack id")
        #     # print(attackId)
        #     # print(maxutil)
        #     maxattackId = attackId

    # print("Finally max utility is ===================>     ", maxutil  )
    # print("Max node at ", maxattackId)
    if length:
        return total_penalty/length
    else:
        return 0

def get_rattack_value(tx,index1,index2):
    print("GET RATTACK VALUE",index1,index2)
    a = tx.run("MATCH (a: Argument {index: $index1})"
                    "MATCH (b: Argument {index: $index2})"
                    "MATCH (a)-[r:RATTACK ]->(b)"
                    "RETURN r.attackValue AS attackval" , index1 = index1,index2= index2)
    for x in a:
        return x["attackval"]
    # print(a[0]["attackval"])
    # return a

def find_next_argument(tx, index,utility1,utility2,depth):
    print("find next argument", index,utility1,utility2,depth)
    a= penalty(tx, index,depth)
    utility1 -= a

    print(utility1,utility2)
    print(a," ========= a")
    possible_next_arguments = tx.run("MATCH (a: Argument {index: $index})"
                    "MATCH (b: Argument)"
                    "MATCH (a)-[r:RATTACK ]->(b)"
                    "RETURN r.attackValue AS attackval, b as attackedNode" , index = index)

    total_utility = -1 # heavy penalty if you cannot attack mine :)
    index= -1

    for possibility in possible_next_arguments:
        attackedNode = possibility["attackedNode"]
        attackval = possibility["attackval"]
        print(attackval)
        if(attackval==None):
            continue
        attackId = attackedNode["index"]
        print(attackId, "================== attackID")
        temp_penalty = penalty(tx,attackId,depth)
        if (attackval - temp_penalty) > (total_utility ):
            total_utility = attackval - temp_penalty
            index = attackId

    utility2 += (total_utility)
    print("INdex == ",index)
    print(utility1,utility2) 
    next_argument_text= ""
    for possibility in possible_next_arguments:
        if possibility["attackedNode"]["index"]==index:
            next_argument_text += "A"
            print(possibility["attackedNode"])
    return utility1,utility2,{"index":index,"text":next_argument_text}
    # result = tx.run("MATCH (a:Argument {index: $next_index}) RETURN a.Argument " , next_index = next_index)
    # for record in result:
    #     print(record["a.Argument"])
    # print(next_index)

def match_similarity(argument1,argument2):
    doc1 = nlp(argument1)
    doc2 = nlp(argument2)
    return doc1.similarity(doc2)

def match_from_all_arguments(tx,data):
    all_arguments = tx.run("MATCH (b: Argument)"
                           "RETURN b.Argument,b.index")
    min_cosine =-2
    min_index =-1 
    for arg in all_arguments:
        a = match_similarity(arg['b.Argument'],data)
        print(a)
        if a>=min_cosine:
            min_cosine=a
            min_index=arg['b.index']
    print("----------------- END ARGUMENT --------------")
    print(min_index, "= ==== min_index")
    return min_index

@app.route("/process",methods=['POST'])
def process():
    data = json.loads(request.data)
    try:
        utility1 = data['utility1'] # utility1 is of the user
        utility2 = data['utility2'] # utility2 is ours
        first_argument = data['first_argument']
        current_argument = data['current_argument']
        prev_index = data['prev_index']
    except:
        return Response("utility1,utility2 ,first_argument,current_argument and prev_index are the required fields",status=400)
    # current_index = apply bert ,till then current argument should be an index
    if first_argument == False:
        change = session.write_transaction(get_rattack_value,prev_index, current_argument)# attack that the user does on us
        utility1 += change
        # current_index = session.write_transaction(match_from_all_attacking_arguments,current_argument,previous_argument)
    else:
        current_index = session.write_transaction(match_from_all_arguments,current_argument)
    utility1,utility2 ,next_argument = session.write_transaction(find_next_argument,current_argument,utility1,utility2,depth=3)
    print({"current_argument":current_index, "utility1":utility1,"utility2":utility2,"next_argument":next_argument})
    return Response({"current_argument":current_argument, "utility1":utility1,"utility2":utility2,"next_argument":next_argument},status=200)

@app.route('/data/add',methods=['POST'])
def postHandler():
    data = json.loads(request.data)
    try:
        file1 = data['file1']
        file2 = data['file2']
        print(file1)
    except:
        return Response("Filenames should be there",status=400)
    session.write_transaction(load_csv,file1,file2)
    return Response("Succesfully added data",status=200)


@app.route('/data/delete/all',methods=['DELETE'])
def deleteHandler():
	session.write_transaction(delete_all)
	return "Succesfully deleted all the data"

@app.route("/")
def hello():            
	return "Running"

if __name__ == "__main__":        
    app.run(port=8080)

driver.close()
