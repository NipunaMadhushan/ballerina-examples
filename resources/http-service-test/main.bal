import ballerina/http;
import ballerina/log;

// Define data structures.
type Product record {|
    int id;
    string name;
    float price;
|};

type OrderRequest record {|
    int productId;
    int quantity;
|};

type Order record {|
    int orderId;
    int productId;
    int quantity;
    float totalPrice;
|};

// Sample data
map<Product> products = {
    "1": {id: 1, name: "Laptop", price: 1200.00},
    "2": {id: 2, name: "Smartphone", price: 800.00},
    "3": {id: 3, name: "Headphones", price: 150.00}
};

map<Order> orders = {};
int orderCounter = 0;

service /shop on new http:Listener(8090) {

    // List available products.
    resource function get products(http:Caller caller) returns error? {
        log:printInfo("Fetching product list");
        http:Response response = new;
        response.setJsonPayload(products);
        response.statusCode = 200;
        check caller->respond(response);
    }

    // Add a new product.
    resource function post product(http:Caller caller, @http:Payload Product product) returns error? {
        log:printInfo("Adding a new product");
        http:Response response = new;

        if (products.hasKey(product.id.toString())) {
            log:printError("Product already exists with product ID:" + product.id.toString());
            response.setTextPayload("Product already exists");
            response.statusCode = 409;
            return;
        }

        products[product.id.toString()] = product;
        log:printInfo("Product added successfully. " + product.toString());
        response.setTextPayload("Product added successfully");
        response.statusCode = 201;
        check caller->respond(response);   
    }

    // Place a new order.
    resource function post 'order(http:Caller caller, @http:Payload OrderRequest orderRequest) returns error? {
        log:printInfo("Received order request");
        http:Response response = new;

        if (!products.hasKey(orderRequest.productId.toString())) {
            log:printError("Product not found with product ID: " + orderRequest.productId.toString());
            response.setTextPayload("Product not found");
            response.statusCode = 404;
            check caller->respond(response);
            return;
        }

        Product product = <Product> products[orderRequest.productId.toString()];
        float totalPrice = product.price * orderRequest.quantity;
        orderCounter += 1;

        Order newOrder = {orderId: orderCounter, productId: orderRequest.productId, quantity: orderRequest.quantity, totalPrice: totalPrice};
        orders[newOrder.orderId.toString()] = newOrder;

        log:printInfo("Order placed successfully. " + newOrder.toString());
        response.setPayload(newOrder.toJson());
        response.statusCode = 201;
        check caller->respond(newOrder);
    }

    // Get order details by ID.
    resource function get 'order/[int orderId](http:Caller caller) returns error? {
        log:printInfo("Fetching order details");
        http:Response response = new;

        if (!orders.hasKey(orderId.toString())) {
            log:printError("Order not found with order ID: " + orderId.toString());
            response.setTextPayload("Order not found");
            response.statusCode = 404;
            check caller->respond(response);
            return;
        }

        Order 'order =  <Order> orders[orderId.toString()];
        log:printInfo("Order details fetched successfully. " + 'order.toString());
        response.setPayload('order.toJson());
        response.statusCode = 200;
        check caller->respond('order);
    }
}
