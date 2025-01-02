import ballerina/test;
import ballerina/http;
import ballerina/io;

http:Client httpClient = check new("http://localhost:8090/shop");

@test:Config
function testProductList() {
    http:Response|error response = httpClient->get("/products");
    if (response is http:Response) {
        test:assertEquals(response.statusCode, 200, "Status code should be 200");
        json|error payload = response.getJsonPayload();
        if (payload is json) {
            map<Product>|error productList = payload.fromJsonWithType();
            if (productList is map<Product>) {
                test:assertEquals(productList, products, "Product list should match");
            } else {
                test:assertFail("Error occurred while fetching product list");
            }
        } else {
            test:assertFail("Error occurred while fetching product list");
        }
    } else {
        test:assertFail("Error occurred while fetching product list");
    }
}

@test:Config
function testAddProduct() {
    json requestPayload = {
        "id": 4, 
        "name": "Laptop Charger", 
        "price": 50.00
    };
    http:Response|error response = httpClient->post("/product", requestPayload);
    if (response is http:Response) {
        test:assertEquals(response.statusCode, 201, "Status code should be 200");
        string|error payload = response.getTextPayload();
        if (payload is string) {
            test:assertEquals(payload, "Product added successfully", "Response message should match");
        } else {
            test:assertFail("Error occurred while fetching product list");
        }
    } else {
        test:assertFail("Error occurred while fetching product list");
    }
}

@test:Config
function testPlaceOrder() {
    json requestPayload = {
        "productId": 1, 
        "quantity": 1
    };
    http:Response|error response = httpClient->post("/order", requestPayload);
    if (response is http:Response) {
        test:assertEquals(response.statusCode, 201, "Status code should be 200");
        json|error payload = response.getJsonPayload();
        io:println(payload);
        if (payload is json) {
            Order|error orderResponse = payload.fromJsonWithType();
            if (orderResponse is Order) {
                string orderNumber = orders.length().toString();
                Order actualOrder = orders.get(orderNumber);            

                test:assertEquals(orderResponse.orderId, actualOrder.orderId, "Order ID should match");
                test:assertEquals(orderResponse.productId, actualOrder.productId, "Product ID should match");
                test:assertEquals(orderResponse.quantity, actualOrder.quantity, "Quantity should match");
                test:assertEquals(orderResponse.totalPrice, actualOrder.totalPrice, "Total price should match");
            } else {
                test:assertFail("Error occurred while fetching product list");
            }
        } else {
            test:assertFail("Error occurred while fetching product list");
        }
    } else {
        test:assertFail("Error occurred while fetching product list");
    }
}

@test:Config
function testGetOrderDetails() {
    json requestPayload = {
        "productId": 1, 
        "quantity": 1
    };
    http:Response|error response = httpClient->post("/order", requestPayload);
    if (response is http:Response) {
        test:assertEquals(response.statusCode, 201, "Status code should be 200");
        json|error payload = response.getJsonPayload();
        io:println(payload);
        if (payload is json) {
            Order|error orderResponse = payload.fromJsonWithType();
            if (orderResponse is Order) {
                string orderNumber = orders.length().toString();
                Order actualOrder = orders.get(orderNumber);            

                test:assertEquals(orderResponse.orderId, actualOrder.orderId, "Order ID should match");
                test:assertEquals(orderResponse.productId, actualOrder.productId, "Product ID should match");
                test:assertEquals(orderResponse.quantity, actualOrder.quantity, "Quantity should match");
                test:assertEquals(orderResponse.totalPrice, actualOrder.totalPrice, "Total price should match");
            } else {
                test:assertFail("Error occurred while fetching product list");
            }
        } else {
            test:assertFail("Error occurred while fetching product list");
        }
    } else {
        test:assertFail("Error occurred while fetching product list");
    }
}

