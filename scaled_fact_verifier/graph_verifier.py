from neo4j import GraphDatabase

class GraphBasedVerifier:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def verify_fact_in_graph(self, fact_triple, scale):
        """Check if fact exists in knowledge graph at given scale"""
        subject, predicate, obj = fact_triple

        with self.driver.session() as session:
            # Query for direct relationship
            query = f"""
            MATCH (s:{scale.title()} {{name: $subject}})-[r:{predicate.upper()}]->(o:{scale.title()} {{name: $obj}})
            RETURN r.confidence as confidence
            """

            result = session.run(query, subject=subject, obj=obj)
            record = result.single()

            if record:
                return record["confidence"]
            else:
                return 0.0

    def get_abstraction(self, entity_name, from_scale, to_scale):
        """Get abstraction mapping between scales"""
        with self.driver.session() as session:
            if from_scale == "entity" and to_scale == "concept":
                function_type = "phi_EC"
            elif from_scale == "concept" and to_scale == "domain":
                function_type = "phi_CD"
            elif from_scale == "entity" and to_scale == "domain":
                function_type = "phi_ED"
            else:
                return None

            query = f"""
            MATCH (from:{from_scale.title()} {{name: $entity_name}})-[:ABSTRACTS_TO {{function: $function}}]->(to:{to_scale.title()})
            RETURN to.name as abstracted_name
            """

            result = session.run(query, entity_name=entity_name, function=function_type)
            record = result.single()

            return record["abstracted_name"] if record else None

# Initialize graph verifier
graph_verifier = GraphBasedVerifier("bolt://localhost:7687", "neo4j", "neo4j@123")