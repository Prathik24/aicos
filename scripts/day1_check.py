import sys                                                                                                        
from pathlib import Path                                                                                          
sys.path.insert(0, str(Path(__file__).parent.parent))                                                             
                                                                                                                
from gateway.gateway import complete    

results = complete(
    task = "smoke_test",
    prompt = "who are you?",
    data_class = "internal"
)

print (results)
