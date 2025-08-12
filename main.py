from mcp.server import FastMCP


mcp = FastMCP("Leaves Manager")


employee_leaves = {
    "E001" : {"balance":18, "history": ["2025-1-10","2025-1-15"]},
    "E002" : {"balance": 20, "history": []}
}



@mcp.tool()
def get_employee_leaves(empid: str) -> str:
    """ check how many leave days are left for employee """
    data = employee_leaves.get(empid)
    if data:
        return f"{empid} leave balance is {data['balance']}"
    return "Employee Id not found"


@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """ Get a personalized greeting """
    return f"Hello {name} ! welcome to mcp server. How can i assist with leave management"


if __name__ == "__main__":
    mcp.run()