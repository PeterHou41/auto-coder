from byzercopilot.common import SourceCode
from byzercopilot import common as FileUtils
import os
from typing import Optional,Generator,List,Dict,Any
from git import Repo
import ast
import importlib
import byzerllm

class Level1PyProject():
    
    def __init__(self,script_path,package_name):
        self.script_path = script_path
        self.package_name = package_name

    def get_imports_from_script(self,file_path):
        script = ""
        with open(file_path, "r") as file:
            script = file.read()
            tree = ast.parse(script, filename=file_path)
        
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        return imports,script

    def filter_imports(self,imports, package_name):
        filtered_imports = []
        for import_ in imports:
            if isinstance(import_, ast.Import):
                for alias in import_.names:
                    if alias.name.startswith(package_name):
                        filtered_imports.append(alias.name)
            elif isinstance(import_, ast.ImportFrom):
                if import_.module and import_.module.startswith(package_name):
                    filtered_imports.append(import_.module)
        return filtered_imports



    def fetch_source_code(self,import_name):
        spec = importlib.util.find_spec(import_name)
        if spec and spec.origin:
            with open(spec.origin, "r") as file:
                return file.read()
        return None
    
    @byzerllm.prompt(render="jinja")
    def auto_implement(self,instruction:str, sources:List[Dict[str,Any]])->str:
        '''
        下面是一些Python 模块以及对应的源码：

        {% for source in sources %}
        #Module:{{ source.module_name }}
        {{ source.source_code }}
        {% endfor %}

        请参考上面的内容，重新实现 script 模块下所有实现是"pass" 的方法。        
        
        {{ instruction }}
            
        '''
        pass

    def run(self):
        imports,script = self.get_imports_from_script(self.script_path)
        filtered_imports = self.filter_imports(imports, self.package_name)
        sources = [] 


        for import_name in filtered_imports:
            source_code = self.fetch_source_code(import_name)
            if source_code:
                sources.append(SourceCode(module_name=import_name, source_code=source_code))            
            else:
                print(f"Could not fetch source code for {import_name}.")

        sources.append(SourceCode(module_name="script", source_code=script))

        sources = [source.dict() for source in sources]
        return self.auto_implement(instruction="", sources=sources)

class PyProject():
    
    def __init__(self,source_dir,git_url:Optional[str]=None,target_file:Optional[str]=None):
        self.directory = source_dir
        self.git_url = git_url        
        self.target_file = target_file       

    def output(self):
        return open(self.target_file, "r").read()                

    def is_python_file(self,file_path):
        return file_path.endswith(".py")

    def read_file_content(self,file_path):
        with open(file_path, "r") as file:
            return file.read()

    def convert_to_source_code(self,file_path):        
        if not FileUtils.is_likely_useful_file(file_path):
            return None
               
        module_name = file_path
        source_code = self.read_file_content(file_path)

        if not FileUtils.has_sufficient_content(source_code,min_line_count=1):
            return None
        
        if FileUtils.is_test_file(source_code):
            return None
        return SourceCode(module_name=module_name, source_code=source_code)
    

    def get_source_codes(self)->Generator[SourceCode,None,None]:
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                file_path = os.path.join(root, file)
                if self.is_python_file(file_path):
                    source_code = self.convert_to_source_code(file_path)
                    if source_code is not None:
                        yield source_code


    def run(self):
        if self.git_url is not None:
            self.clone_repository()

        if self.target_file is None:                
            for code in self.get_source_codes():
                print(f"##File: {code.module_name}")
                print(code.source_code)                
        else:            
            with open(self.target_file, "w") as file:
                for code in self.get_source_codes():
                    file.write(f"##File: {code.module_name}\n")
                    file.write(f"{code.source_code}\n\n")
                    
    
    def clone_repository(self):   
        if self.git_url is None:
            raise ValueError("git_url is required to clone the repository")
             
        if os.path.exists(self.directory):
            print(f"Directory {self.directory} already exists. Skipping cloning.")
        else:
            print(f"Cloning repository {self.git_url} into {self.directory}")
            Repo.clone_from(self.git_url, self.directory)
