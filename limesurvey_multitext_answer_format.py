keywords = ["this", "concat", "trim"]

with open('q.txt', 'r') as file:
    lines = file.readlines()
    for i in range(len(lines)):
        line = lines[i].replace('"', '').replace(",", "").strip()

        formatted = "trim(this) == '"+line+"'"
        if any(keyword in line for keyword in keywords):
            for keyword in keywords:
                if keyword in line:
                    line = line.replace(keyword, ".+")
                    
            formatted = 'regexMatch("/^'+line+'$/", trim(this))'

        if i == len(lines) - 1:
            print(formatted)
        else:
            print(formatted + " or ")
