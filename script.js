function addToCart(productId) {
    fetch('/add_to_cart', {
        method: 'POST',
        body: JSON.stringify({ product_id: productId }),
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.text())
    .then(data => alert(data))
    .catch(error => console.error('Error:', error));
}
