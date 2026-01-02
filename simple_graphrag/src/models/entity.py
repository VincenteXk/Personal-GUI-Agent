"""
实体数据模型
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Iterable, Callable, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .graph import Graph


@dataclass
class PropertyDefinition:
    """
    属性定义，定义某个类下的属性结构

    Attributes:
        name: 属性名称
        required: 是否为必选属性（默认False）
        value_required: 该属性的值是否必须（默认False）
        description: 属性的通用描述（可选）
    """

    name: str
    required: bool = False
    value_required: bool = False
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "required": self.required,
            "value_required": self.value_required,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PropertyDefinition":
        """从字典创建属性定义"""
        return cls(
            name=data["name"],
            required=data.get("required", False),
            value_required=data.get("value_required", False),
            description=data.get("description"),
        )


@dataclass
class ClassDefinition:
    """
    类定义，定义类的结构和属性

    Attributes:
        name: 类名称
        properties: 该类的属性定义列表
        description: 类的描述（可选）
    """

    name: str
    properties: List[PropertyDefinition] = field(default_factory=list)
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "properties": [prop.to_dict() for prop in self.properties],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClassDefinition":
        """从字典创建类定义"""
        return cls(
            name=data["name"],
            description=data.get("description"),
            properties=[
                PropertyDefinition.from_dict(prop_data)
                for prop_data in data.get("properties", [])
            ],
        )

    def property_names(self) -> Set[str]:
        return {p.name for p in self.properties}

    def required_properties(self) -> List[PropertyDefinition]:
        return [p for p in self.properties if p.required]

    def add_property(self, prop_def: PropertyDefinition) -> None:
        """
        添加属性定义到类中（如果属性已存在则跳过）

        Args:
            prop_def: 属性定义
        """
        # 检查属性是否已存在
        if prop_def.name not in self.property_names():
            self.properties.append(prop_def)

    def validate_instance(
        self, class_instance: "ClassInstance"
    ) -> tuple[List[str], List[str], List[str]]:
        """
        验证类实例的属性是否符合该类定义

        Returns:
            (缺失的必选属性列表, 无效属性列表, 缺少必填值的属性列表)
        """
        missing_required: List[str] = []
        invalid_properties: List[str] = []
        missing_required_values: List[str] = []

        # 检查必选属性
        for prop_def in self.required_properties():
            if not class_instance.has_property(prop_def.name):
                missing_required.append(prop_def.name)

        valid_property_names = self.property_names()
        prop_def_dict = {p.name: p for p in self.properties}

        for prop_name in class_instance.properties.keys():
            if prop_name not in valid_property_names:
                invalid_properties.append(prop_name)
                continue
            prop_def = prop_def_dict.get(prop_name)
            if prop_def and prop_def.value_required:
                pv = class_instance.get_property(prop_name)
                if not pv or pv.value is None or str(pv.value).strip() == "":
                    missing_required_values.append(prop_name)

        return missing_required, invalid_properties, missing_required_values


@dataclass
class PropertyValue:
    """
    属性值，表示节点在某个类下的某个属性的具体值

    Attributes:
        property_name: 属性名称
        value: 属性值（可选）
    """

    property_name: str
    value: Optional[str] = None


@dataclass
class ClassInstance:
    """
    类实例，表示节点拥有的某个类及其属性值

    Attributes:
        class_name: 类名称
        properties: 该类下的属性值字典，key为属性名，value为PropertyValue
    """

    class_name: str
    properties: Dict[str, PropertyValue] = field(default_factory=dict)

    def set_property(
        self,
        property_name: str,
        value: Optional[str] = None,
    ) -> None:
        """
        设置属性值

        Args:
            property_name: 属性名称
            value: 属性值（可选）
        """
        self.properties[property_name] = PropertyValue(
            property_name=property_name, value=value
        )

    def get_property(self, property_name: str) -> Optional[PropertyValue]:
        """
        获取属性值

        Args:
            property_name: 属性名称

        Returns:
            属性值对象，如果不存在返回None
        """
        return self.properties.get(property_name)

    def has_property(self, property_name: str) -> bool:
        """
        检查是否拥有指定属性

        Args:
            property_name: 属性名称

        Returns:
            如果拥有该属性返回True，否则返回False
        """
        return property_name in self.properties

    def remove_property(self, property_name: str) -> None:
        """
        移除属性

        Args:
            property_name: 属性名称
        """
        if property_name in self.properties:
            del self.properties[property_name]


@dataclass
class PredefinedEntity:
    """
    预定义实体（System 内置/基础实体）

    说明：
    - System 是“抽象架构定义”，Graph 是“具体实例”
    - 预定义实体属于系统配置的一部分，Graph 初始化时可选择自动注入
    """

    name: str
    description: str = ""
    classes: List[str] = field(default_factory=list)

    def to_entity(self, system: Optional["System"] = None) -> "Entity":
        e = Entity(name=self.name, description=self.description)
        for c in self.classes:
            e.add_class(c, system=system)
        return e

    @classmethod
    def from_dict(cls, data: dict) -> "PredefinedEntity":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", "") or "",
            classes=list(data.get("classes", []) or []),
        )


@dataclass
class System:
    """
    System：一个“系统”的抽象架构定义（可实例化的配置对象）

    - 包含：类定义（含属性定义）、预定义实体
    - Graph 使用某个 System，形成具体实例（实体/节点/关系）
    """

    name: str = "default"
    description: str = ""
    classes: Dict[str, ClassDefinition] = field(default_factory=dict)  # key: UPPER
    predefined_entities: List[PredefinedEntity] = field(default_factory=list)
    _class_added_listeners: List[Callable[[ClassDefinition], None]] = field(
        default_factory=list, repr=False
    )

    # -----------------------------
    # 原子功能：类定义的增量扩展（只增不删）
    # -----------------------------

    def add_class_definition(self, class_def: ClassDefinition) -> ClassDefinition:
        """
        添加/扩展一个类定义（单调合并，只允许新增，不允许删除）

        - 已存在同名类：只会新增属性/增强约束/更新描述（若提供）
        - 不会删除旧属性，也不会把 required/value_required 从 True 降为 False
        """
        key = class_def.name.upper()
        if key not in self.classes:
            self.classes[key] = class_def
            self._notify_class_added(self.classes[key])
            return self.classes[key]

        existing = self.classes[key]

        # description：新值非空则覆盖（增强信息）
        if class_def.description and str(class_def.description).strip():
            existing.description = class_def.description

        # properties：按 name 合并；required/value_required 只增强不削弱
        existing_by_name = {p.name: p for p in existing.properties}
        for p in class_def.properties:
            if p.name not in existing_by_name:
                existing.properties.append(p)
                existing_by_name[p.name] = p
                continue
            old = existing_by_name[p.name]
            old.required = bool(old.required or p.required)
            old.value_required = bool(old.value_required or p.value_required)
            if p.description and str(p.description).strip():
                old.description = p.description

        # 视为“系统变更”（尽管是扩展已有类），也触发通知
        self._notify_class_added(existing)
        return existing

    def add_property(
        self,
        class_name: str,
        prop: PropertyDefinition,
    ) -> ClassDefinition:
        """向指定类增量添加/增强一个属性定义（只增不删）"""
        class_def = self.get_class_definition(class_name)
        if not class_def:
            raise ValueError(f"类 '{class_name}' 未在 System 中定义")
        return self.add_class_definition(
            ClassDefinition(name=class_def.name, description=None, properties=[prop])
        )

    def remove_class_definition(self, class_name: str) -> None:
        """不支持删除类定义（按需求：只能新增，不能删除）"""
        raise NotImplementedError("System 不支持删除类定义（只能新增/扩展）")

    def register_class(self, class_def: ClassDefinition) -> None:
        # 兼容旧接口：等价于“只增不删”的增量扩展
        self.add_class_definition(class_def)

    def get_class_definition(self, class_name: str) -> Optional[ClassDefinition]:
        return self.classes.get(class_name.upper())

    def get_all_classes(self) -> List[str]:
        # 返回“类的原始名称”（用于提示词/展示）；不返回内部 UPPER key
        return [cd.name for cd in self.classes.values()]

    def get_all_class_definitions_dict(self) -> Dict[str, dict]:
        return {k: v.to_dict() for k, v in self.classes.items()}

    def load_from_dict(self, config_dict: Dict[str, Dict]) -> None:
        """
        从 {class_name: {description, properties: [...]}} 加载类定义
        """
        for class_name, config in (config_dict or {}).items():
            properties: List[PropertyDefinition] = []
            for prop_data in config.get("properties", []) or []:
                properties.append(
                    PropertyDefinition(
                        name=prop_data["name"],
                        required=prop_data.get("required", False),
                        value_required=prop_data.get("value_required", False),
                        description=prop_data.get("description"),
                    )
                )
            self.register_class(
                ClassDefinition(
                    name=class_name,
                    description=config.get("description"),
                    properties=properties,
                )
            )

    def validate_class_instance(
        self, class_instance: "ClassInstance"
    ) -> tuple[List[str], List[str], List[str]]:
        class_def = self.get_class_definition(class_instance.class_name)
        if not class_def:
            return [], list(class_instance.properties.keys()), []
        return class_def.validate_instance(class_instance)

    # -----------------------------
    # 原子功能：监听 system 的类变更（给 Graph 等使用）
    # -----------------------------

    def subscribe_class_added(
        self, callback: Callable[[ClassDefinition], None]
    ) -> None:
        if callback not in self._class_added_listeners:
            self._class_added_listeners.append(callback)

    def unsubscribe_class_added(
        self, callback: Callable[[ClassDefinition], None]
    ) -> None:
        if callback in self._class_added_listeners:
            self._class_added_listeners.remove(callback)

    def _notify_class_added(self, class_def: ClassDefinition) -> None:
        for cb in list(self._class_added_listeners):
            try:
                cb(class_def)
            except Exception:
                # listener 不应影响 system 本身的可用性
                pass

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "classes": {k: v.to_dict() for k, v in self.classes.items()},
            "base_entities": [
                {
                    "name": e.name,
                    "description": e.description,
                    "classes": list(e.classes),
                }
                for e in self.predefined_entities
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "System":
        """
        支持直接接收 SystemBuilder/pipeline 产生的 dict：
        { classes: {...}, base_entities: [...] }
        """
        system = cls(
            name=data.get("name", "default"),
            description=data.get("description", "") or "",
        )

        # classes：既可能是 {class_name: {description, properties...}}，
        # 也可能是 {CLASS_UPPER: {name, description, properties...}}（来自旧序列化）
        raw_classes = data.get("classes", {}) or {}
        for k, v in raw_classes.items():
            if isinstance(v, dict) and "name" in v:
                system.register_class(ClassDefinition.from_dict(v))
            else:
                system.register_class(
                    ClassDefinition.from_dict({"name": k, **(v or {})})
                )

        for ent in data.get("base_entities", []) or []:
            if isinstance(ent, dict):
                system.predefined_entities.append(PredefinedEntity.from_dict(ent))

        return system

    @classmethod
    def from_config_dict(cls, config: dict, use_base_system: bool = False) -> "System":
        """
        从 config.yaml 加载的配置字典创建 System

        Args:
            config: 配置字典，应包含 'classes' 或 'base_system' 字段
            use_base_system: 是否使用 base_system（如果为 True 且存在 base_system，优先使用它）

        Returns:
            System 实例
        """
        system = cls()

        # 决定使用哪个配置源
        if use_base_system and "base_system" in config:
            # 使用 base_system.classes 和 base_system.entities
            classes_config = config["base_system"].get("classes", {})
            # 兼容两种字段名：entities（新）和 base_entities（旧）
            predefined_entities = config["base_system"].get("entities") or config[
                "base_system"
            ].get("base_entities", [])
        else:
            # 使用顶级 classes 和 entities/base_entities
            classes_config = config.get("classes", {})
            predefined_entities = config.get("entities") or config.get(
                "base_entities", []
            )

        system.load_from_dict(classes_config)

        for entity_data in predefined_entities:
            pred = PredefinedEntity.from_dict(entity_data)
            system.predefined_entities.append(pred)

        return system

    @classmethod
    def from_config_file(cls, config_path, use_base_system: bool = False) -> "System":
        """
        从 config.yaml 文件创建 System

        Args:
            config_path: config.yaml 文件路径（Path 或 str）
            use_base_system: 是否使用 base_system.classes（如果为 True 且存在 base_system，优先使用它）

        Returns:
            System 实例
        """
        import yaml
        from pathlib import Path

        config_path = Path(config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return cls.from_config_dict(config, use_base_system=use_base_system)


@dataclass
class ClassNode:
    """
    类节点，表示实体的某个类作为独立节点

    例如："小红书:购物平台" 是一个类节点，连接到中心节点"小红书"

    Attributes:
        entity_name: 所属实体的名称
        class_name: 类名称
        description: 类节点的描述（可选，默认为类的描述）
        created_at: 创建时间
        updated_at: 更新时间
    """

    entity_name: str
    class_name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    @property
    def node_id(self) -> str:
        """获取类节点的唯一标识符，格式为 entity_name:class_name"""
        return f"{self.entity_name}:{self.class_name}"

    def __hash__(self) -> int:
        """用于去重和集合操作"""
        return hash(self.node_id.upper())

    def __eq__(self, other) -> bool:
        """类节点相等性判断"""
        if not isinstance(other, ClassNode):
            return False
        return self.node_id.upper() == other.node_id.upper()

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "entity_name": self.entity_name,
            "class_name": self.class_name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClassNode":
        """从字典创建类节点"""
        created_at = None
        updated_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            entity_name=data["entity_name"],
            class_name=data["class_name"],
            description=data.get("description"),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class ClassMasterNode:
    """
    类主节点，表示“类本身”作为独立节点（跨实体共享）

    例如：类“购物平台”是一个类主节点；“淘宝:购物平台”“京东:购物平台”是类节点。
    类主节点用于描述该类的总体信息/通用属性（如“用户对电子产品感兴趣”）。

    Attributes:
        class_name: 类名称（也是该节点的唯一标识）
        description: 类主节点的描述（通常等于类定义的描述）
        created_at: 创建时间
        updated_at: 更新时间
    """

    class_name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    @property
    def node_id(self) -> str:
        """获取类主节点的唯一标识符（即类名）"""
        return self.class_name

    def __hash__(self) -> int:
        """用于去重和集合操作"""
        return hash(self.node_id.upper())

    def __eq__(self, other) -> bool:
        """类主节点相等性判断"""
        if not isinstance(other, ClassMasterNode):
            return False
        return self.node_id.upper() == other.node_id.upper()

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "class_name": self.class_name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClassMasterNode":
        """从字典创建类主节点"""
        created_at = None
        updated_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            class_name=data["class_name"],
            description=data.get("description"),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class Entity:
    """实体类，表示知识图谱中的中心节点"""

    name: str
    description: str
    classes: List[ClassInstance] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 内部属性：绑定的 Graph 引用（由 Graph.add_entity 自动设置）
    _graph: Optional["Graph"] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    @property
    def graph(self) -> Optional["Graph"]:
        """获取绑定的 Graph"""
        return self._graph

    def _get_system(self) -> Optional[System]:
        """获取绑定的 System（通过 Graph）"""
        return self._graph.system if self._graph else None

    def validate_against_system(self, system: System, strict: bool = True) -> None:
        """
        基于 System 校验/修复实体的类实例

        - strict=True：遇到未定义类/缺少必填值/无效属性 -> 抛异常
        - strict=False：自动过滤未定义类、移除无效属性、补齐必选属性（值必填则置空字符串）
        """
        valid_classes: List[ClassInstance] = []
        for class_instance in self.classes:
            class_def = system.get_class_definition(class_instance.class_name)
            if not class_def:
                if strict:
                    raise ValueError(
                        f"实体 '{self.name}' 包含未定义的类: {class_instance.class_name}. "
                        f"System 已定义类: {system.get_all_classes()}"
                    )
                else:
                    import warnings

                    warnings.warn(
                        f"实体 '{self.name}' 包含未定义的类 '{class_instance.class_name}'，已自动过滤。",
                        UserWarning,
                    )
                    continue

            missing_required, invalid_properties, missing_required_values = (
                class_def.validate_instance(class_instance)
            )

            if missing_required or invalid_properties or missing_required_values:
                if strict:
                    msg = f"实体 '{self.name}' 的类 '{class_instance.class_name}' "
                    if missing_required:
                        msg += f"缺少必选属性: {missing_required}. "
                    if invalid_properties:
                        msg += f"包含无效属性: {invalid_properties}. "
                    if missing_required_values:
                        msg += f"缺少必填值的属性: {missing_required_values}. "
                    msg += f"类定义: {[p.name for p in class_def.properties]}"
                    raise ValueError(msg)
                else:
                    import warnings

                    # 自动创建无效属性的定义
                    if invalid_properties:
                        for prop_name in invalid_properties:
                            # 获取属性的当前值用于推断类型
                            prop_value = class_instance.get_property(prop_name)

                            # 创建新的属性定义
                            new_prop_def = PropertyDefinition(
                                name=prop_name,
                                required=False,  # 自动创建的属性默认为可选
                                value_required=False,  # 值也是可选的
                                description=f"自动创建的属性（从实体 '{self.name}' 推断）",
                            )

                            # 添加到类定义中
                            class_def.add_property(new_prop_def)

                            warnings.warn(
                                f"实体 '{self.name}' 的类 '{class_instance.class_name}' "
                                f"包含未定义的属性 '{prop_name}'，已自动创建属性定义。",
                                UserWarning,
                            )

                    # 提示其他修复
                    if missing_required or missing_required_values:
                        warnings.warn(
                            f"实体 '{self.name}' 的类 '{class_instance.class_name}' "
                            f"缺少必选属性 {missing_required} 或缺少必填值 {missing_required_values}，已自动修复。",
                            UserWarning,
                        )

                    # 补齐必选属性
                    for prop_def in class_def.required_properties():
                        if not class_instance.has_property(prop_def.name):
                            class_instance.set_property(
                                prop_def.name,
                                value="" if prop_def.value_required else None,
                            )

            valid_classes.append(class_instance)

        self.classes = valid_classes

    def add_class(
        self, class_name: str, system: Optional[System] = None
    ) -> ClassInstance:
        """
        添加类到实体

        Args:
            class_name: 要添加的类名称
            system: System 实例（可选，如果实体已绑定 Graph 则自动使用 Graph 的 system）

        Returns:
            创建的类实例

        Raises:
            ValueError: 如果类未定义或 system 缺失
        """
        # 优先使用传入的 system，否则尝试从绑定的 Graph 获取
        effective_system = system or self._get_system()

        class_def = (
            effective_system.get_class_definition(class_name)
            if effective_system
            else None
        )
        if effective_system and not class_def:
            raise ValueError(
                f"类 '{class_name}' 未定义. System 已定义类: {effective_system.get_all_classes()}"
            )

        # 检查是否已存在该类
        for existing_class in self.classes:
            if existing_class.class_name.upper() == class_name.upper():
                return existing_class

        # 创建新的类实例
        class_instance = ClassInstance(class_name=class_name)

        # 为必选属性创建属性值（如果值也是必填的，先创建空值占位）
        if class_def:
            for prop_def in class_def.required_properties():
                class_instance.set_property(
                    prop_def.name, value="" if prop_def.value_required else None
                )

        self.classes.append(class_instance)
        self.updated_at = datetime.now()
        return class_instance

    def remove_class(self, class_name: str) -> None:
        """
        从实体移除类

        Args:
            class_name: 要移除的类名称
        """
        self.classes = [
            c for c in self.classes if c.class_name.upper() != class_name.upper()
        ]
        self.updated_at = datetime.now()

    def has_class(self, class_name: str) -> bool:
        """
        检查实体是否拥有指定类

        Args:
            class_name: 类名称

        Returns:
            如果实体拥有该类返回True，否则返回False
        """
        return any(c.class_name.upper() == class_name.upper() for c in self.classes)

    def get_class_instance(self, class_name: str) -> Optional[ClassInstance]:
        """
        获取指定类的实例

        Args:
            class_name: 类名称

        Returns:
            类实例，如果不存在返回None
        """
        for class_instance in self.classes:
            if class_instance.class_name.upper() == class_name.upper():
                return class_instance
        return None

    def set_property_value(
        self,
        class_name: str,
        property_name: str,
        value: Optional[str] = None,
        system: Optional[System] = None,
    ) -> None:
        """
        设置实体在某个类下的某个属性的值

        Args:
            class_name: 类名称
            property_name: 属性名称
            value: 属性值（可选）
            system: System 实例（可选，如果实体已绑定 Graph 则自动使用 Graph 的 system）

        Raises:
            ValueError: 如果类不存在或属性无效
        """
        class_instance = self.get_class_instance(class_name)
        if not class_instance:
            raise ValueError(
                f"实体 '{self.name}' 不拥有类 '{class_name}'. "
                f"拥有的类为: {[c.class_name for c in self.classes]}"
            )

        # 优先使用传入的 system，否则尝试从绑定的 Graph 获取
        effective_system = system or self._get_system()
        if effective_system:
            class_def = effective_system.get_class_definition(class_name)
            if not class_def:
                raise ValueError(f"类 '{class_name}' 未在 System 中定义")
            valid_property_names = class_def.property_names()
            if property_name not in valid_property_names:
                raise ValueError(
                    f"类 '{class_name}' 不包含属性 '{property_name}'. "
                    f"可用属性为: {list(valid_property_names)}"
                )
            prop_def = next(
                (p for p in class_def.properties if p.name == property_name), None
            )
            if prop_def and prop_def.value_required:
                if value is None or str(value).strip() == "":
                    raise ValueError(f"属性 '{property_name}' 的值是必填的，不能为空")

        class_instance.set_property(property_name, value)
        self.updated_at = datetime.now()

    def get_property_value(
        self, class_name: str, property_name: str
    ) -> Optional[PropertyValue]:
        """
        获取实体在某个类下的某个属性的值

        Args:
            class_name: 类名称
            property_name: 属性名称

        Returns:
            属性值对象，如果不存在返回None
        """
        class_instance = self.get_class_instance(class_name)
        if not class_instance:
            return None
        return class_instance.get_property(property_name)

    def __hash__(self) -> int:
        """用于去重和集合操作"""
        return hash(self.name.upper())

    def __eq__(self, other) -> bool:
        """实体相等性判断（基于名称）"""
        if not isinstance(other, Entity):
            return False
        return self.name.upper() == other.name.upper()

    def update_description(self, new_description: str) -> None:
        """更新实体描述（用于增量更新时合并描述）"""
        if new_description and new_description.strip():
            self.description = new_description
            self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "classes": [
                {
                    "class_name": ci.class_name,
                    "properties": {
                        prop_name: {
                            "property_name": pv.property_name,
                            "value": pv.value,
                        }
                        for prop_name, pv in ci.properties.items()
                    },
                }
                for ci in self.classes
            ],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict, strict_validation: bool = False) -> "Entity":
        """
        从字典创建实体

        Args:
            data: 包含实体数据的字典
            strict_validation: 是否严格验证类（默认False，用于加载旧数据时更宽容）
        """
        created_at = None
        updated_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        # 处理类实例
        classes = []
        for class_data in data.get("classes", []):
            class_instance = ClassInstance(class_name=class_data["class_name"])
            for prop_name, prop_data in class_data.get("properties", {}).items():
                class_instance.set_property(
                    property_name=prop_data.get("property_name", prop_name),
                    value=prop_data.get("value"),
                )
            classes.append(class_instance)

        entity = cls(
            name=data["name"],
            description=data["description"],
            classes=classes,
            created_at=created_at,
            updated_at=updated_at,
        )
        return entity
