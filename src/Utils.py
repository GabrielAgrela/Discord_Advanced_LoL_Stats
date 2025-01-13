def translate(text: str) -> str:
        """stuff like CLASSIC to SUMMONER'S RIFT"""
        if text == "CLASSIC":
            return "Summoner's Rift"
        elif text == "ARAM":
            return "ARAM"
        elif text == "URF":
            return "URF"
        elif text == "ULTBOOK":
            return "Ultimate Book"
        elif text == "CHERRY":
            return "Arena"
        elif text == "NEXUSBLITZ":
            return "Nexus Blitz"
        elif text == "STRAWBERRY":
            return "Swarm"
        
        #reverse
        elif text == "Summoner's Rift":
            return "CLASSIC"
        elif text == "Arena":
            return "CHERRY"
        elif text == "Nexus Blitz":
            return "NEXUSBLITZ"
        elif text == "Swarm":
            return "STRAWBERRY"
        elif text == "Ultimate Book":
            return "ULTBOOK"
        elif text == "URF":
            return "URF"
        elif text == "ARAM":
            return "ARAM"
        return text
