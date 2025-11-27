from enum import Enum


class ReferenceType(str, Enum):
    """참조 타입"""
    SALES_ORDER = "판매"
    BUY = "구매"
    MANUFACTURE = "제조"
    SHIPPING = "배송"
    RECEIVING = "입고"
    
    STORING = "보관"
    OTHER = "기타"
    
    CUSTOMER_SERVICE = "고객서비스"
    SOCIAL_MEDIA = "소셜미디어"