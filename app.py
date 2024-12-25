from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import numpy as np

app = Flask(__name__)


@app.route('/scrape', methods=['GET'])
def scrape_google_shopping():
    product_name = request.args.get('product_name')
    limit = request.args.get('limit', default=15, type=int)

    if product_name:
        formatted_product_name = product_name.replace(' ', '+')
    else:
        return jsonify({"error": "Product name is required"}), 400

    search_url = f"https://www.google.com/search?tbm=shop&q={formatted_product_name}&tbs=mr:1,avg_rating:400"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch data from Google"}), response.status_code

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    prices = []

    products = soup.select(".sh-dgr__content")
    count = 0  # Biến đếm số lượng sản phẩm

    for product in products:
        if count >= limit:
            break
        try:
            title_elem = product.select_one(".tAxDx")
            title = title_elem.text.strip() if title_elem else "N/A"

            price_elem = product.select_one(".a8Pemb")
            price_text = price_elem.text.strip() if price_elem else "N/A"

            price_cleaned = re.sub(r'[^\d]', '', price_text)
            price = int(price_cleaned) if price_cleaned.isdigit() else None

            shop_elem = product.select_one(".aULzUe")
            shop_name = shop_elem.text.strip() if shop_elem else "N/A"

            link_elem = product.select_one(".xCpuod")
            shop_url = f"https://www.google.com{link_elem['href']}" if link_elem else "N/A"

            if price is not None:
                prices.append(price)

            results.append({
                "ProductName": title,
                "Price": price,
                "ShopName": shop_name,
                "ShopUrl": shop_url,
            })

            count += 1  # Tăng biến đếm sau mỗi lần thêm sản phẩm
        except Exception as e:
            print(f"Error scraping product: {e}")

    if not prices:
        return jsonify({"message": "No results found"}), 404

    # Tính toán khoảng giá lệch về phía cao
    q1 = np.percentile(prices, 25)
    q3 = np.percentile(prices, 75)
    iqr = q3 - q1

    lower_bound = q1 - 0.2*iqr
    upper_bound = q3 + 1.5 * iqr

    print(f"Q1: {q1}, Q3: {q3}, IQR: {iqr}")
    print(f"Valid price range: {lower_bound} - {upper_bound}")

    # Lọc sản phẩm trong khoảng giá hợp lệ
    filtered_results = [
        product for product in results
        if product["Price"] is not None and lower_bound <= product["Price"] <= upper_bound
    ]

    # Sắp xếp theo giá từ cao xuống thấp
    sorted_results = sorted(
        filtered_results, key=lambda x: x["Price"], reverse=True)

    if not sorted_results:
        return jsonify({"message": "No valid results found"}), 404

    return jsonify(sorted_results)


if __name__ == '__main__':
    app.run(debug=True)
