package io.github.gabbloquet.ailab.exp001.catalog.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.groups.Tuple.tuple;

import java.math.BigDecimal;
import java.util.List;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.DepartmentNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidSearchQueryException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.*;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

class CatalogRulesTest {

    private static final StoreId STORE = new StoreId("S01");

    private static Product product(String sku, String price) {
        return product(sku, price, "Casque");
    }

    private static Product product(String sku, String price, String type) {
        return new Product(new SkuCode(sku), "Produit " + sku, "Marque", "Audio", type, new BigDecimal(price));
    }

    private static StockLine stock(String sku, int onHand, int reserved) {
        return new StockLine(new SkuCode(sku), STORE, onHand, reserved);
    }

    private static Catalog catalog(List<Product> products, List<StockLine> stock) {
        return new Catalog(products, List.of(new Store(STORE, "Magasin test", "Lyon")), stock);
    }

    private static List<String> skus(List<Alternative> alternatives) {
        return alternatives.stream().map(alternative -> alternative.product().sku().value()).toList();
    }

    private static List<Alternative> alternativesOf(Catalog catalog, String sku) {
        return catalog.alternatives(new SkuCode(sku), STORE);
    }

    @Nested
    class Similar {

        private static final String P = "P-00001";
        private static final String OTHER_TYPE = "P-00002";
        private static final String HIGH = "P-00010";
        private static final String LOW = "P-00011";
        private static final String OUTSIDE = "P-00012";

        private List<String> similarOf(Catalog catalog, String sku) {
            return catalog.similar(new SkuCode(sku)).stream().map(product -> product.sku().value()).toList();
        }

        @Test
        void areTheSameTypeWithinThePriceBandWhateverTheStock() {
            var catalog = catalog(
                    List.of(product(P, "100.00"), product(LOW, "80.00"), product(HIGH, "120.00"),
                            product(OTHER_TYPE, "100.00", "Enceinte"), product(OUTSIDE, "120.01")),
                    List.of(stock(LOW, 0, 0)));

            assertThat(similarOf(catalog, P)).containsExactlyInAnyOrder(LOW, HIGH);
        }

        @Test
        void areSortedByPriceGapThenSkuWithoutCap() {
            var catalog = catalog(
                    List.of(product(P, "100.00"), product("P-00034", "110.00"), product("P-00033", "90.00"),
                            product("P-00032", "95.00"), product("P-00031", "119.00")),
                    List.of());

            assertThat(similarOf(catalog, P)).containsExactly("P-00032", "P-00033", "P-00034", "P-00031");
        }
    }

    private static final Catalog HOME_AND_AUDIO = new Catalog(
            List.of(
                    new Product(new SkuCode("P-00001"), "Pellisse Cafetière G9", "Pellisse", "Maison", "Cafetière",
                            new BigDecimal("101.99")),
                    new Product(new SkuCode("P-00002"), "Pellisse Bouilloire K2", "Pellisse", "Maison", "Bouilloire",
                            new BigDecimal("39.90")),
                    new Product(new SkuCode("P-00003"), "Veldric Casque K8", "Veldric", "Audio", "Casque",
                            new BigDecimal("100.00"))),
            List.of(),
            List.of());

    @Nested
    class Alternatives {

        private static final String P = "P-00001";
        private static final String Q = "P-00002";
        private static final String HIGH = "P-00010";
        private static final String LOW = "P-00011";
        private static final String EMPTY = "P-00020";
        private static final String RESERVED = "P-00021";
        private static final String NOLINE = "P-00022";
        private static final String A = "P-00031";
        private static final String B = "P-00032";
        private static final String C = "P-00033";
        private static final String D = "P-00034";

        @Test
        void includeBothBoundsOfThePriceBand() {
            var catalog = catalog(
                    List.of(product(P, "100.00"), product(LOW, "80.00"), product(HIGH, "120.00")),
                    List.of(stock(LOW, 1, 0), stock(HIGH, 1, 0)));

            assertThat(skus(alternativesOf(catalog, P))).containsExactly(HIGH, LOW);
        }

        @Test
        void excludePricesJustOutsideTheBand() {
            var catalog = catalog(
                    List.of(product(P, "100.00"), product(LOW, "79.99"), product(HIGH, "120.01")),
                    List.of(stock(LOW, 1, 0), stock(HIGH, 1, 0)));

            assertThat(alternativesOf(catalog, P)).isEmpty();
        }

        @Test
        void excludeTheProductItself() {
            var catalog = catalog(List.of(product(P, "100.00")), List.of(stock(P, 5, 0)));

            assertThat(alternativesOf(catalog, P)).isEmpty();
        }

        @Test
        void requireTheSameType() {
            var catalog = catalog(
                    List.of(product(P, "100.00"), product(Q, "100.00", "Enceinte")),
                    List.of(stock(Q, 1, 0)));

            assertThat(alternativesOf(catalog, P)).isEmpty();
        }

        @Test
        void requireUnitsAvailableInTheStore() {
            var catalog = catalog(
                    List.of(product(P, "100.00"), product(EMPTY, "100.00"), product(RESERVED, "100.00"),
                            product(NOLINE, "100.00")),
                    List.of(stock(EMPTY, 0, 0), stock(RESERVED, 2, 2)));

            assertThat(alternativesOf(catalog, P)).isEmpty();
        }

        @Test
        void areSortedByPriceGapThenSkuAndCappedAtThree() {
            var catalog = catalog(
                    List.of(product(P, "100.00"), product(D, "110.00"), product(C, "90.00"),
                            product(B, "95.00"), product(A, "119.00")),
                    List.of(stock(A, 1, 0), stock(B, 1, 0), stock(C, 1, 0), stock(D, 1, 0)));

            assertThat(skus(alternativesOf(catalog, P))).containsExactly(B, C, D);
        }

        @Test
        void carryTheQuantityAvailableForSale() {
            var catalog = catalog(
                    List.of(product(P, "100.00"), product(Q, "100.00")),
                    List.of(stock(Q, 5, 2)));

            assertThat(alternativesOf(catalog, P)).singleElement()
                    .extracting(Alternative::available).isEqualTo(3);
        }

        @Test
        void doNotExistForAnUnknownProduct() {
            var catalog = catalog(List.of(product(Q, "100.00")), List.of(stock(Q, 1, 0)));

            assertThat(alternativesOf(catalog, "P-99999")).isEmpty();
        }
    }

    @Nested
    class StoresWithStock {

        @Test
        void listStoresWithUnitsAvailableSortedByStoreId() {
            var p = product("P-00001", "100.00");
            var catalog = new Catalog(
                    List.of(p),
                    List.of(new Store(new StoreId("S02"), "Magasin 2", "Nantes"),
                            new Store(new StoreId("S01"), "Magasin 1", "Lyon"),
                            new Store(new StoreId("S03"), "Magasin 3", "Lille")),
                    List.of(new StockLine(p.sku(), new StoreId("S02"), 1, 0),
                            new StockLine(p.sku(), new StoreId("S01"), 4, 0),
                            new StockLine(p.sku(), new StoreId("S03"), 2, 2)));

            assertThat(catalog.storesWithStock(p.sku()))
                    .extracting(stock -> stock.store().storeId().value(), StoreStock::available)
                    .containsExactly(
                            tuple("S01", 4),
                            tuple("S02", 1));
        }
    }

    @Nested
    class Search {

        private final Catalog catalog = HOME_AND_AUDIO;

        private List<String> found(String query, String department) {
            return catalog.search(query, department).stream().map(p -> p.sku().value()).toList();
        }

        @Test
        void ignoresCaseAndAccents() {
            assertThat(found("CAFETIERE", null)).containsExactly("P-00001");
        }

        @Test
        void requiresEveryWordToMatch() {
            assertThat(found("pellisse cafetière", null)).containsExactly("P-00001");
            assertThat(found("pellisse casque", null)).isEmpty();
        }

        @Test
        void searchesTheBrand() {
            assertThat(found("pellisse", null)).containsExactly("P-00002", "P-00001");
        }

        @Test
        void filtersOnTheDepartmentIgnoringCase() {
            assertThat(found("k", "audio")).containsExactly("P-00003");
        }

        @Test
        void sortsResultsByName() {
            assertThat(found("pellisse", " ")).containsExactly("P-00002", "P-00001");
        }

        @Test
        void returnsNothingWhenNothingMatches() {
            assertThat(found("aspirateur", null)).isEmpty();
        }

        @Test
        void rejectsABlankQuery() {
            assertThatThrownBy(() -> catalog.search("  ", null))
                    .isInstanceOf(InvalidSearchQueryException.class)
                    .hasMessage("Search query must not be blank");
        }

        @Test
        void rejectsAnUnknownDepartment() {
            assertThatThrownBy(() -> catalog.search("casque", "Hifi"))
                    .isInstanceOf(DepartmentNotFoundException.class)
                    .hasMessage("Unknown department: Hifi");
        }

        @Test
        void returnsNothingForAKnownDepartmentWithoutMatch() {
            assertThat(found("casque", "Maison")).isEmpty();
        }
    }

    @Nested
    class Browse {

        private List<String> browsed(String department) {
            return HOME_AND_AUDIO.browse(department).stream().map(p -> p.sku().value()).toList();
        }

        @Test
        void listsADepartmentSortedByName() {
            assertThat(browsed("maison")).containsExactly("P-00002", "P-00001");
        }

        @Test
        void listsTheWholeCatalogWithoutDepartment() {
            assertThat(browsed(null)).containsExactly("P-00002", "P-00001", "P-00003");
            assertThat(browsed(" ")).containsExactly("P-00002", "P-00001", "P-00003");
        }

        @Test
        void rejectsAnUnknownDepartment() {
            assertThatThrownBy(() -> HOME_AND_AUDIO.browse("Hifi"))
                    .isInstanceOf(DepartmentNotFoundException.class)
                    .hasMessage("Unknown department: Hifi");
        }
    }
}
